import json
import time

from pydantic import ValidationError

from services.Agentic.MainAgents.ExecutiveControlMode.database import (
    add_agent_memory,
    get_agent_memories,
    get_all_context,
    log_execution_step,
    save_context_val,
    update_task_status,
)
from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlModels import (
    ECNState,
    ToolCall,
)
from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlPrompts import (
    EVALUATOR_SYSTEM_PROMPT,
    REASONER_SYSTEM_PROMPT,
)
from services.Config import config
from services.CustomLibs.LLM import call_llm
from services.CustomLibs.sandbox import sandbox


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def task_context_builder(state: ECNState) -> ECNState:
    t0 = time.perf_counter()
    iteration = state.iteration + 1
    print(
        f"[TaskContextBuilder] iteration {iteration} — loading context and memory from SQLite..."
    )

    db_context = get_all_context(state.task_id)
    memories = get_agent_memories(
        memory_type="SHORT_TERM", task_context_id=state.task_id
    )
    db_memory = [m["value"] for m in memories]

    updated_context = {**db_context, "iteration": iteration}
    save_context_val(state.task_id, "iteration", iteration)

    log_execution_step(
        task_id=state.task_id,
        step_number=iteration,
        node_name="TaskContextBuilder",
        action_type="context_compilation",
        inputs={"iteration": iteration},
        outputs={
            "context_keys": list(updated_context.keys()),
            "memory_count": len(db_memory),
        },
        duration_ms=_elapsed_ms(t0),
    )

    return state.model_copy(
        update={
            "context": updated_context,
            "memory": db_memory,
            "iteration": iteration,
        }
    )


def task_reasoner(state: ECNState) -> ECNState:
    t0 = time.perf_counter()
    print(f"[TaskReasoner] reasoning for task: '{state.task}'")

    prompt = (
        f"Goal: {state.task}\n"
        f"Iteration: {state.iteration}/{config.MAX_LOOPS}\n"
        f"Context: {state.context}\n"
        f"Past Memory Logs: {state.memory}"
    )

    llm_response = call_llm(prompt, system_prompt=REASONER_SYSTEM_PROMPT)
    last_line = llm_response.strip().splitlines()[-1] if llm_response else ""
    print(f"  [Reasoner Output]: {last_line}")

    routing = (
        "task_completed" if "ROUTE: done" in llm_response else "requires_tool_execution"
    )

    log_execution_step(
        task_id=state.task_id,
        step_number=state.iteration,
        node_name="TaskReasoner",
        action_type="reasoning",
        inputs={"prompt_length": len(prompt)},
        outputs={"routing": routing, "response_length": len(llm_response)},
        duration_ms=_elapsed_ms(t0),
    )

    return state.model_copy(
        update={
            "reasoning": llm_response,
            "reasoner_routing": routing,
        }
    )


def task_executor(state: ECNState) -> ECNState:
    t0 = time.perf_counter()
    print("[TaskExecutor] executing action step in Sandbox...")

    reasoning = state.reasoning
    exec_response = ""
    try:
        start_idx = reasoning.find("{")
        end_idx = reasoning.rfind("}")

        if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
            raise ValueError("No JSON block found in response.")

        json_str = reasoning[start_idx : end_idx + 1]
        raw_tool_call = json.loads(json_str)

        # Auto-heal: If the model returned arguments directly without the tool/args envelope
        if isinstance(raw_tool_call, dict) and "tool" not in raw_tool_call:
            if "filename" in raw_tool_call and "content" in raw_tool_call:
                raw_tool_call = {"tool": "write_file", "args": raw_tool_call}
            elif "filename" in raw_tool_call:
                raw_tool_call = {"tool": "read_file", "args": raw_tool_call}
            elif "code" in raw_tool_call:
                raw_tool_call = {"tool": "run_python", "args": raw_tool_call}
            elif "command" in raw_tool_call:
                raw_tool_call = {"tool": "run_shell", "args": raw_tool_call}
            elif not raw_tool_call:
                raw_tool_call = {"tool": "list_files", "args": {}}

        validated_call = ToolCall(**raw_tool_call)

        tool_name = validated_call.tool
        args = validated_call.args

        print(
            f"  [Executor] Invoking {tool_name} with args: {args.model_dump().keys()}"
        )

        from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlModels import (
            ReadFileArgs,
            RunPythonArgs,
            RunShellArgs,
            WriteFileArgs,
        )

        if tool_name == "run_python":
            assert isinstance(args, RunPythonArgs)
            exec_response = sandbox.run_python(args.code)
        elif tool_name == "run_shell":
            assert isinstance(args, RunShellArgs)
            exec_response = sandbox.run_shell(args.command)
        elif tool_name == "write_file":
            assert isinstance(args, WriteFileArgs)
            exec_response = sandbox.write_file(args.filename, args.content)
        elif tool_name == "read_file":
            assert isinstance(args, ReadFileArgs)
            exec_response = sandbox.read_file(args.filename)
        elif tool_name == "list_files":
            exec_response = sandbox.list_files()
        else:
            exec_response = f"Error: Unknown tool '{tool_name}'"

    except ValidationError as e:
        print(f"  [Executor] Pydantic validation failed: {e}")
        exec_response = f"Tool Execution Error: Invalid arguments for tool. {e}"
    except Exception as e:
        print(f"  [Executor] Failed to parse/execute tool call: {e}")
        exec_response = f"Error parsing JSON tool call from reasoner: {e}. Output pure JSON wrapped in {{ }} matching the ToolCall schema."

    print(f"  [Executor Output]: {exec_response[:120]}...")

    save_context_val(state.task_id, "last_execution_output", exec_response[:500])
    save_context_val(state.task_id, "execution_status", "executed")

    log_execution_step(
        task_id=state.task_id,
        step_number=state.iteration,
        node_name="TaskExecutor",
        action_type="tool_execution",
        inputs={"reasoning_length": len(state.reasoning)},
        outputs={"response_length": len(exec_response)},
        duration_ms=_elapsed_ms(t0),
    )

    return state.model_copy(
        update={
            "context": get_all_context(state.task_id),
            "execution_result": {"status": "executed", "output": exec_response},
        }
    )


def task_evaluator(state: ECNState) -> ECNState:
    t0 = time.perf_counter()
    print("[TaskEvaluator] evaluating step result via LLM...")

    if state.iteration >= config.MAX_LOOPS:
        print(
            f"  [Evaluator] Max iterations ({config.MAX_LOOPS}) reached — forcing task_failed."
        )
        log_execution_step(
            task_id=state.task_id,
            step_number=state.iteration,
            node_name="TaskEvaluator",
            action_type="evaluation",
            inputs={"reason": "max_iterations_reached"},
            outputs={"evaluation_status": "task_failed"},
            duration_ms=_elapsed_ms(t0),
        )
        return state.model_copy(update={"evaluation_status": "task_failed"})

    exec_output = state.execution_result.get("output", "")
    prompt = (
        f"Goal: {state.task}\n"
        f"Execution Output:\n{exec_output[:1000]}\n\n"
        f"Evaluate the execution output against the Goal and determine the verdict as defined in the system prompt.\n"
        f"Respond with exactly one of these on the last line:\n"
        f"VERDICT: SUCCESS\n"
        f"VERDICT: RETRY\n"
        f"VERDICT: FAILURE"
    )

    eval_response = call_llm(prompt, system_prompt=EVALUATOR_SYSTEM_PROMPT)
    last_line = eval_response.strip().splitlines()[-1] if eval_response else ""
    print(f"  [Evaluator Output]: {last_line}")

    if "VERDICT: FAILURE" in eval_response:
        status = "task_failed"
    elif "VERDICT: RETRY" in eval_response:
        status = "step_error"
    else:
        status = "step_success"

    log_execution_step(
        task_id=state.task_id,
        step_number=state.iteration,
        node_name="TaskEvaluator",
        action_type="evaluation",
        inputs={"exec_output_length": len(exec_output)},
        outputs={
            "evaluation_status": status,
            "eval_response_length": len(eval_response),
        },
        duration_ms=_elapsed_ms(t0),
    )

    return state.model_copy(update={"evaluation_status": status})


def task_memory_manager(state: ECNState) -> ECNState:
    t0 = time.perf_counter()
    print("[TaskMemoryManager] committing step log to SQLite agent_memory table...")

    exec_snippet = state.execution_result.get("output", "")[:200]
    log_entry = (
        f"[iter {state.iteration}] "
        f"Eval={state.evaluation_status} | "
        f"Exec: {exec_snippet}"
    )

    add_agent_memory(
        key=f"step_log_iter_{state.iteration}",
        value=log_entry,
        memory_type="SHORT_TERM",
        task_context_id=state.task_id,
    )

    memories = get_agent_memories(
        memory_type="SHORT_TERM", task_context_id=state.task_id
    )
    updated_memory = [m["value"] for m in memories]

    log_execution_step(
        task_id=state.task_id,
        step_number=state.iteration,
        node_name="TaskMemoryManager",
        action_type="memory_commitment",
        inputs={"log_entry_length": len(log_entry)},
        outputs={"total_memory_count": len(updated_memory)},
        duration_ms=_elapsed_ms(t0),
    )

    return state.model_copy(update={"memory": updated_memory})


def task_finalizer(state: ECNState) -> ECNState:
    t0 = time.perf_counter()
    print("[TaskFinalizer] summarizing final result and saving to tasks table...")

    status = "FAILED" if state.evaluation_status == "task_failed" else "COMPLETED"
    update_task_status(
        task_id=state.task_id,
        status=status,
        final_output=state.reasoning[:2000],
    )

    log_execution_step(
        task_id=state.task_id,
        step_number=state.iteration,
        node_name="TaskFinalizer",
        action_type="finalization",
        inputs={"final_output_length": len(state.reasoning)},
        outputs={"status": "COMPLETED"},
        duration_ms=_elapsed_ms(t0),
    )

    return state.model_copy()
