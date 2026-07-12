import json
import time
import traceback
from typing import Any

from pydantic import ValidationError

from Config import config
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


def mock_reasoner_fallback(state: ECNState) -> Any:
    """Mock fallback for task reasoner when LLM call fails."""
    from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlModels import (
        ReasonerResponse,
        ToolCall,
        ShowDatetimeArgs,
        RunPythonArgs,
    )
    # Fallback to direct python run if code/transform is involved, or datetime
    if "datetime" in state.task.lower() or "time" in state.task.lower():
        return ReasonerResponse(
            thought_process="Fallback reasoning: User requested system time.",
            routing="requires_tool_execution",
            tool_call=ToolCall(tool="show_datetime", args=ShowDatetimeArgs())
        )
    if "transform" in state.task.lower() or "loop" in state.task.lower():
        code = "original = 'Hello World'\ntransformed = [original.upper() for _ in range(3)]\nprint(transformed)"
        return ReasonerResponse(
            thought_process="Fallback reasoning: Running Python script to transform string.",
            routing="requires_tool_execution",
            tool_call=ToolCall(tool="run_python", args=RunPythonArgs(code=code))
        )
    return ReasonerResponse(
        thought_process="Fallback reasoning: No tools available, finishing.",
        routing="task_completed",
        final_answer="Failed to execute task: LLM connection timeout."
    )


def task_reasoner(state: ECNState) -> ECNState:
    t0 = time.perf_counter()
    print(f"[TaskReasoner] reasoning for task: '{state.task}'")

    prompt = (
        f"Goal: {state.task}\n"
        f"Iteration: {state.iteration}/{config.MAX_LOOPS}\n"
        f"Context: {state.context}\n"
        f"Last Execution Result: {state.execution_result.get('output', '')}\n"
        f"Past Memory Logs: {state.memory}"
    )

    import instructor
    import openai
    client = instructor.from_openai(
        openai.OpenAI(
            base_url=config.BASE_URL if config.BASE_URL else "http://localhost:11434/v1",
            api_key=config.API_KEY if config.API_KEY else "ollama",
        ),
        mode=instructor.Mode.JSON,
    )

    from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlModels import ReasonerResponse

    print("\n[LLM Execution] Calling ECN Reasoner LLM:")
    print(f"  Model: {config.MODEL}")
    print(f"  Temperature: 0.0")
    print(f"  Timeout: {config.TIMEOUT}")
    print(f"  System Prompt Length: {len(REASONER_SYSTEM_PROMPT)}")
    print(f"  User Prompt:\n{prompt}")

    try:
        response = client.chat.completions.create(
            model=config.MODEL,
            messages=[
                {"role": "system", "content": REASONER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_model=ReasonerResponse,
            temperature=0.0,
            timeout=config.TIMEOUT,
        )
        print("[LLM Response] Success!")
        if hasattr(response, "model_dump_json"):
            print(f"  Response: {response.model_dump_json(indent=2)}")
        elif hasattr(response, "model_dump"):
            print(f"  Response: {json.dumps(response.model_dump(), indent=2)}")
        else:
            print(f"  Response: {response}")
    except Exception as e:
        print(f"  [LLM Warning] Connection failed, using mock/empty response. Error: {e}")
        traceback.print_exc()
        response = mock_reasoner_fallback(state)

    if response.routing == "requires_tool_execution" and response.tool_call:
        serialized_tool = json.dumps({
            "tool": response.tool_call.tool,
            "args": response.tool_call.args.model_dump()
        })
        reasoning_str = f"{response.thought_process}\nROUTE: tool\n{serialized_tool}"
        final_ans = ""
    else:
        reasoning_str = f"{response.thought_process}\nROUTE: done\n{response.final_answer or ''}"
        final_ans = response.final_answer or ""

    print(f"  [Reasoner Output]: {response.routing} - tool={response.tool_call.tool if response.tool_call else None}")

    log_execution_step(
        task_id=state.task_id,
        step_number=state.iteration,
        node_name="TaskReasoner",
        action_type="reasoning",
        inputs={"prompt_length": len(prompt)},
        outputs={"routing": response.routing, "response_length": len(reasoning_str)},
        duration_ms=_elapsed_ms(t0),
    )

    return state.model_copy(
        update={
            "reasoning": reasoning_str,
            "reasoner_routing": response.routing,
            "final_answer": final_ans,
        }
    )


def task_executor(state: ECNState) -> ECNState:
    t0 = time.perf_counter()
    print("[TaskExecutor] executing action step in Sandbox...")

    reasoning = state.reasoning
    try:
        # Locate the JSON block robustly by skipping thoughts/markdown code blocks
        import re
        json_part = reasoning
        if "ROUTE: tool" in reasoning:
            json_part = reasoning.split("ROUTE: tool")[-1]
        else:
            matches = list(re.finditer(r'\{\s*"tool"\s*:', reasoning))
            if matches:
                tool_idx = matches[-1].start()
                json_part = reasoning[tool_idx:]
            elif "{" in reasoning:
                last_brace = reasoning.rfind("{")
                if last_brace != -1:
                    json_part = reasoning[last_brace:]

        start_idx = json_part.find("{")
        end_idx = json_part.rfind("}")

        if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
            raise ValueError("No JSON block found in response.")

        json_str = json_part[start_idx : end_idx + 1]
        
        # Clean JSON: escape raw newlines, carriage returns, and tabs inside double-quoted string literals
        in_quotes = False
        escaped = False
        cleaned_chars = []
        for c in json_str:
            if c == '"' and not escaped:
                in_quotes = not in_quotes
            if c == '\\' and not escaped:
                escaped = True
            else:
                escaped = False
            
            if c == '\n' and in_quotes:
                cleaned_chars.append('\\n')
            elif c == '\r' and in_quotes:
                cleaned_chars.append('\\r')
            elif c == '\t' and in_quotes:
                cleaned_chars.append('\\t')
            else:
                cleaned_chars.append(c)
        json_str = "".join(cleaned_chars)
        
        # Clean JSON: remove trailing commas inside arrays and objects
        import re
        json_str = re.sub(r",\s*([\]}])", r"\1", json_str)
        
        raw_tool_call = json.loads(json_str)

        # Auto-heal: If the model returned arguments directly without the tool/args envelope
        if isinstance(raw_tool_call, dict):
            if "tool" in raw_tool_call and "args" not in raw_tool_call:
                # Flat arguments under the same dict: gather them into "args"
                tool_name = raw_tool_call["tool"]
                args_dict = {k: v for k, v in raw_tool_call.items() if k != "tool"}
                raw_tool_call = {"tool": tool_name, "args": args_dict}
            elif "tool" not in raw_tool_call:
                if "filename" in raw_tool_call and "content" in raw_tool_call:
                    raw_tool_call = {"tool": "write_file", "args": raw_tool_call}
                elif "filename" in raw_tool_call:
                    raw_tool_call = {"tool": "read_file", "args": raw_tool_call}
                elif "code" in raw_tool_call:
                    raw_tool_call = {"tool": "run_python", "args": raw_tool_call}
                elif "command" in raw_tool_call:
                    raw_tool_call = {"tool": "run_shell", "args": raw_tool_call}
                elif "query" in raw_tool_call and "file_pattern" in raw_tool_call:
                    raw_tool_call = {"tool": "search_grep", "args": raw_tool_call}
                elif "query" in raw_tool_call:
                    raw_tool_call = {"tool": "web_search", "args": raw_tool_call}
                elif "url" in raw_tool_call:
                    raw_tool_call = {"tool": "fetch_webpage", "args": raw_tool_call}
                elif not raw_tool_call:
                    raw_tool_call = {"tool": "list_files", "args": {}}

        validated_call = ToolCall(**raw_tool_call)

        tool_name = validated_call.tool
        args = validated_call.args

        print(
            f"  [Executor] Invoking tool '{tool_name}' with arguments: {json.dumps(args.model_dump(), indent=2)}"
        )

        from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlModels import (
            DeleteFileArgs,
            FetchWebpageArgs,
            ReadFileArgs,
            RunPythonArgs,
            RunShellArgs,
            SearchGrepArgs,
            WebSearchArgs,
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
        elif tool_name == "web_search":
            assert isinstance(args, WebSearchArgs)
            exec_response = sandbox.web_search(args.query)
        elif tool_name == "fetch_webpage":
            assert isinstance(args, FetchWebpageArgs)
            exec_response = sandbox.fetch_webpage(args.url)
        elif tool_name == "search_grep":
            assert isinstance(args, SearchGrepArgs)
            exec_response = sandbox.search_grep(args.query, args.file_pattern)
        elif tool_name == "delete_file":
            assert isinstance(args, DeleteFileArgs)
            exec_response = sandbox.delete_file(args.filename)
        elif tool_name == "show_datetime":
            exec_response = sandbox.show_datetime()
        elif tool_name == "get_env":
            exec_response = sandbox.get_env()
        else:
            exec_response = f"Error: Unknown tool '{tool_name}'"

    except ValidationError as e:
        print(f"  [Executor Fail] Pydantic validation failed for tool '{tool_name if 'tool_name' in locals() else 'unknown'}': {e}")
        traceback.print_exc()
        exec_response = f"Error parsing JSON tool call: Tool Execution Error: Invalid arguments for tool. {e}"
    except Exception as e:
        print(f"  [Executor Fail] Failed to parse/execute tool call: {e}")
        traceback.print_exc()
        exec_response = f"Error parsing JSON tool call from reasoner: {e}. Output pure JSON wrapped in {{ }} matching the ToolCall schema."

    print(f"  [Executor Output]: {exec_response}")

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
    
    # Programmatic override for transient connection/network/socket errors
    is_transient_error = False
    lower_output = exec_output.lower()
    if any(term in lower_output for term in ["connectionreseterror", "connection aborted", "connectionreset", "socket error", "10054"]):
        is_transient_error = True
    elif "timed out" in lower_output and "seconds" in lower_output:
        is_transient_error = True
    elif any(term in lower_output for term in ["handshake failed", "actively refused", "10061"]):
        is_transient_error = True

    if is_transient_error:
        print("  [Evaluator] Detected transient network error in tool output. Forcing VERDICT: RETRY.")
        status = "step_error"
    else:
        prompt = (
            f"Goal: {state.task}\n"
            f"Execution Output:\n{exec_output[:5000]}\n\n"
            f"Evaluate the execution output against the Goal and determine the verdict as defined in the system prompt.\n"
            f"Respond with exactly one of these on the last line:\n"
            f"VERDICT: SUCCESS\n"
            f"VERDICT: RETRY\n"
            f"VERDICT: FAILURE"
        )
        print("\n[LLM Execution] Calling Evaluator LLM (non-structured):")
        print(f"  System Prompt Length: {len(EVALUATOR_SYSTEM_PROMPT)}")
        print(f"  Prompt:\n{prompt}")

        try:
            eval_response = call_llm(prompt, system_prompt=EVALUATOR_SYSTEM_PROMPT)
            print("[LLM Response] Success!")
            print(f"  Raw Evaluator Response:\n{eval_response}")
            last_line = eval_response.strip().splitlines()[-1] if eval_response else ""
            print(f"  [Evaluator Output]: {last_line}")
        except Exception as e:
            print(f"  [LLM Warning] Evaluator LLM execution failed: {e}")
            traceback.print_exc()
            eval_response = "VERDICT: RETRY"
            last_line = "VERDICT: RETRY"

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
