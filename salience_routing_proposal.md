# Salience Routing & Channel Loop Optimization Proposal

This document analyzes the routing and loop execution failure when processing state/identity-changing user inputs (e.g., `"Your name is 'Sun' from now on"`) and proposes concrete changes to prompts and code routing logic to ensure system stability.

---

## 🔍 Root Cause Analysis

### 1. Misrouted Subgraph & Channel
When the user says `"Your name is 'Sun' from now on"`, the `SalienceRouter` erroneously selects:
* **Target Subgraph:** `DefaultMode` (instead of `ExecutiveControlMode`)
* **Prompt Channel:** `inner_channel` (instead of `outer_channel`)

#### Why did the LLM make this choice?
* **"Your name"** contains a self-referential pronoun. Without explicit rules, the LLM associates "Your/Self/Internal Name" with "internal memory consolidation, resting, internal knowledge graph patterns, or quiet reflection on existing knowledge."
* The input doesn't look like an active question or computation, so the LLM avoided `ExecutiveControlMode`, treating it as an internal metadata refinement.

### 2. The Internal Graph Loop Failure
Once routed to `DefaultMode` with `inner_channel`, the `LoopSubgraph` executes:
1. **Collector Node:** Runs in "inner" mode using `CollectorNodePromptInner`. It queries the existing database using `tool_ingest_internal_stream(source="llm_input")` and only gets `current_internal_state`. **It completely ignores the raw user input text (`input_text`).**
2. **Data Loss:** Because the raw user input is never parsed, the fact that the agent's name should be "Sun" is never collected.
3. **Infinite Loop:** The subgraph continues iterating `Collector -> Organizer -> Reflector -> Integrator`. The `Reflector` and `Integrator` look at the unchanged graph, find no external updates, and try to perform latent pattern optimization indefinitely (or until max iterations are reached), completely unaware of the user's name change command.

---

## 💡 Proposed Prompt Adjustments

To resolve this, we propose updating the router's system prompt to clearly separate **External Stimulus/Directives** from **Quiet Self-Reflection/Resting**.

### Proposed Change in `SaliencePrompts.py`
Replace `SALIENCE_ROUTER_SYSTEM_PROMPT` with the following:

```python
SALIENCE_ROUTER_SYSTEM_PROMPT = """You are the SalienceRouter inside a Salience Mode Network.
Your task is to observe the user's input and decide which cognitive subgraph to route it to, and which prompt channel to use.

Available subgraphs:
1. ExecutiveControlMode:
   - Use this for general queries, questions, user tasks, calculations, coding, tool executions, system operations, and active instructions (such as settings configuration, user command executions, or agent identity updates).
   - Examples: "Show me the current system datetime.", "Your name is 'Sun' from now on.", "Hi!", "Compile the project."
   
2. DefaultMode:
   - This is strictly a REST, reflection, and background memory consolidation mode.
   - Use this ONLY when the input is noise, blank, non-actionable, or explicitly requests resting/internal knowledge graph refinement/consolidation without any active tasks.
   - Do NOT route general questions, active commands, or actionable instructions here.

For the prompt channel (strictly one of: 'inner_channel' or 'outer_channel'):
- Use 'outer_channel' for ALL external user prompts, inputs, and commands that contain new text, new facts, or active instructions from the user. Any input requiring the parsing of the user's raw message MUST use 'outer_channel'.
- Use 'inner_channel' ONLY when the user explicitly requests background self-reflection, resting, or quiet optimization of the existing knowledge graph without providing new external details to parse.
"""
```

#### Why this prompt works:
1. **Explicit Identity Example:** It lists `"Your name is 'Sun' from now on."` directly under `ExecutiveControlMode` as an example of an active instruction.
2. **Strict Channel Clause:** It explicitly dictates that **any** input requiring parsing of the user's raw message must use `outer_channel`. This prevents `inner_channel` from hijacking user commands.

---

## 🛠️ Proposed Code Safeguards

Even with perfect prompts, LLMs can occasionally hallucinate. We should add safeguards in the code to handle channel discrepancies.

### Safeguard A: Channel Auto-Escalation in `collector_node`
If the router selects `inner_channel` but there is a pending, unparsed `input_text` that contains active commands, the collector node should dynamically escalate to `outer_channel`.

In `services/services/Agentic/MainAgents/DefaultMode/LoopSubgraphAgent/LoopAgentNodes.py`:
```python
def collector_node(state: GraphState) -> GraphState:
    channel = state.channel
    user_input = state.input_text.strip()
    
    # SAFEGUARD: If we are in inner_channel but have an active, unparsed external instruction
    if channel == "inner_channel" and user_input and not any(k in user_input.lower() for k in ["rest", "reflect", "consolidate"]):
        print(f"  [Safeguard] Active user input detected in inner_channel. Auto-escalating to outer_channel to parse: '{user_input}'")
        channel = "outer_channel"
```

### Safeguard B: Dynamic Context Injection in Inner Prompts
If `inner_channel` is executed, make the raw user input available to the `CollectorNodePromptInner` as secondary context so that the LLM has a chance to see it if it needs to update identity:

```python
# In LoopAgentPrompts.py:
CollectorNodePromptInner = """[SYSTEM ROLE]
...
[INPUT CONTEXT]
Current Recall Knowledge Graph: {current_internal_state}
Raw Secondary Context: {input_text}
...
"""
```

### Safeguard C: Loop Termination in `_loop_or_exit`
Ensure the loop halts early if no new quads are generated or if no internal directives are being executed, preventing infinite cycles on the same graph state:

```python
def _loop_or_exit(state: GraphState) -> str:
    # If no new quads were proposed or merged during this iteration, exit the loop
    if state.iteration >= 3 or not state.has_state_changed:
        return "exit"
    return "loop"
```
