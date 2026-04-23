# Concur Task Trees (CTT) - Research & Design Proposals

## 1. Overview

ConcurTaskTrees (CTT) is a notation for task model specifications developed for interactive application design. It provides:
- **Hierarchical tree structure** for task decomposition
- **Temporal operators** defining execution relationships between concurrent/sequential tasks
- **Rich expressiveness** for concurrent, parallel, interrupted, and optional behaviors

## 2. Current Implementation

Your codebase already implements CTT in `Lib/CTT/ctt_types.py`:

### 2.1 Temporal Operators (CTTTaskOperator)

```python
CTTTaskOperator: TypeAlias = Literal[
    "interleaving",       # T1 ||| T2 (concurrent, order independent)
    "synchronization",   # T1 |[]| T2 (concurrent, synchronize on some actions)
    "choice",           # T1 [] T2 (execute one or the other)
    "sequence",         # T1 >> T2 (sequential execution)
    "suspend_resume",   # T1 |> T2 (T2 interrupts T1, T1 resumes after T2)
    "order_independence",# T1 |=| T2 (T1 and T2 in any order, not concurrent)
    "disabling",        # T1 [> T2 (T2 can interrupt and terminate T1)
]
```

### 2.2 Core Types

```python
class CTTTask(TypedDict, total=False):
    task_id: Required[str]
    title: Required[str]
    status: Required[TaskStatus]
    task_type: NotRequired[TaskType]
    operator: NotRequired[CTTTaskOperator]
    prompt: NotRequired[str]
    assigned_agent: NotRequired[str]
    parent_task_id: NotRequired[str]
    dependency_task_ids: NotRequired[List[str]]
    sub_task_ids: NotRequired[List[str]]

class CTTState(TypedDict, total=False):
    tasks: Required[Dict[str, CTTTask]]
    edges: NotRequired[List[CTTEdge]]
    root_task_ids: Required[List[str]]
    ready_queue: NotRequired[List[str]]
    running_task_ids: NotRequired[List[str]]
    completed_task_ids: NotRequired[List[str]]
    failed_task_ids: NotRequired[List[str]]
    run: NotRequired[CTTRunContext]
```

### 2.3 Task Status Flow

```
pending → ready → running → completed
                    ↓ failed
                    ↓ cancelled
```

## 3. CTT Temporal Operators (Reference)

| Operator | Symbol | Meaning |
|----------|--------|---------|
| Sequential Enabling | >> | T1 must complete before T2 starts |
| Sequential Enabling Info | []>> | T1 output is input to T2 |
| Suspend-Resume | \|> | T2 suspends T1, T1 resumes after T2 |
| Disabling | [> | T2 can interrupt and terminate T1 |
| Synchronisation | \|[]\| | Tasks sync at certain points |
| Interleaving | \|\|\| | Concurrent, order independent |
| Order Independence | \|=\| | Non-concurrent, any order |
| Choice | [] | Execute one OR the other |
| Optionality | [T] | Task T is optional |
| Iteration | T* | Task T repeats |

## 4. Design Proposals: LLM Task Creation & Todos

### 4.1 Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Prompt Input                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              CTT Task Decomposer                            │
│  (LLM generates CTT structure from natural language)        │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   ┌──────────────┐       ┌──────────────┐
   │ CTTTask Tree │─────▶ │ Execution    │
   │ (State)      │       │ Engine       │
   └──────────────┘       └──────────────┘
          │                       │
          ▼                       ▼
   ┌──────────────────────────────────────┐
   │     TodoWrite Integration            │
   │  (Sync CTT tasks ↔ Todo list)        │
   └──────────────────────────────────────┘
```

### 4.2 LLM Task Decomposition Prompt

```python
CTT_DECOMPOSITION_PROMPT = """You are a task decomposition expert using ConcurTaskTrees (CTT).

Given a user request, decompose it into a CTT task tree with:
- Hierarchical tasks (parent → subtasks)
- Temporal operators between sibling tasks
- Dependencies where required

Available operators:
- "sequence": >> (sequential, T1 then T2)
- "choice": [] (one OR the other)  
- "interleaving": ||| (concurrent, independent)
- "order_independence": |=| (any order, not concurrent)
- "suspend_resume": |> (T2 interrupts T1, T1 resumes)
- "disabling": [> (T2 can terminate T1)
- "optional": [T] (optional task)

Output JSON format:
{{
    "root_task_id": "root_1",
    "tasks": {{
        "task_id": {{...task data...}}
    }},
    "edges": [{{...relationship...}}]
}}
"""
```

### 4.3 CTT-to-Todo Synchronization

```python
class CTTTodoSync:
    """Sync CTT tasks with todo list representation."""
    
    # Mapping CTT status → todo status
    STATUS_MAP = {
        "pending": "pending",
        "ready": "pending", 
        "running": "in_progress",
        "completed": "completed",
        "failed": "cancelled",
        "cancelled": "cancelled",
        "blocked": "pending",
    }
    
    # Mapping CTT operator → visual indicator
    OPERATOR_SYMBOLS = {
        "sequence": ">>",
        "interleaving": "|||", 
        "choice": "[]",
        "order_independence": "|=|",
        "suspend_resume": "|>",
        "disabling": "[>",
        "synchronization": "|[]|",
    }
    
    @classmethod
    def ctt_to_todo_items(cls, state: CTTState) -> List[TodoItem]:
        """Convert CTT state to todo list items."""
        items = []
        for task_id, task in state["tasks"].items():
            symbol = cls.OPERATOR_SYMBOLS.get(task.get("operator", ""), "")
            title = f"{symbol} {task['title']}" if symbol else task['title']
            
            items.append(TodoItem(
                id=task_id,
                content=title,
                status=cls.STATUS_MAP.get(task["status"], "pending"),
                priority=task.get("priority", 0),
            ))
        
        # Sort by execution order
        return cls._topological_sort(items, state)
```

### 4.4 Task Execution Engine

```python
class CTTExecutor:
    """Execute CTT task tree respecting temporal operators."""
    
    OPERATOR_HANDLERS = {
        "sequence": lambda tasks: _execute_sequential(tasks),
        "choice": lambda tasks: _execute_choice(tasks),
        "interleaving": lambda tasks: _execute_parallel(tasks),
        "order_independence": lambda tasks: _execute_independent(tasks),
        "suspend_resume": lambda tasks: _execute_suspend_resume(tasks),
        "disabling": lambda tasks: _execute_disabling(tasks),
    }
    
    async def execute_task(self, task: CTTTask, context: CTTState) -> Any:
        """Execute a single task based on its type."""
        handlers = {
            "llm_inference": self._execute_llm,
            "tool_execution": self._execute_tool,
            "human_review": self._execute_human_review,
            "data_processing": self._execute_data,
            "sub_workflow": self._execute_subworkflow,
        }
        
        handler = handlers.get(task.get("task_type", "llm_inference"))
        return await handler(task, context)
    
    async def execute_operator(
        self, 
        operator: str, 
        subtasks: List[CTTTask],
        context: CTTState
    ) -> List[Any]:
        """Execute subtasks according to temporal operator."""
        handler = self.OPERATOR_HANDLERS.get(operator)
        if not handler:
            raise ValueError(f"Unknown operator: {operator}")
        
        return await handler(subtasks, context)
```

### 4.5 LLM-Aware Task Creation

```python
from typing import Optional
import uuid

class CTTTaskFactory:
    """Factory for creating CTT tasks from various inputs."""
    
    TASK_TYPE_PROMPTS = {
        "llm_inference": "Use LLM for generation/reasoning",
        "tool_execution": "Execute a specific tool",
        "human_review": "Request human input/approval",
        "data_processing": "Transform or analyze data",
        "sub_workflow": "Execute a nested task tree",
    }
    
    @classmethod
    def from_natural_language(
        cls,
        description: str,
        goal: str,
        context: Optional[Dict] = None
    ) -> CTTState:
        """Create CTT state from natural language description.
        
        This would typically call an LLM to decompose the request
        into a proper CTT structure.
        """
        # Placeholder - actual implementation would use LLM
        task_id = str(uuid.uuid4())
        
        return CTTState(
            tasks={
                task_id: CTTTask(
                    task_id=task_id,
                    title=description,
                    status="ready",
                    task_type="llm_inference",
                    prompt=f"Goal: {goal}\nContext: {context}",
                )
            },
            root_task_ids=[task_id],
            ready_queue=[task_id],
        )
    
    @classmethod
    def from_template(
        cls,
        template: str,
        parameters: Dict
    ) -> CTTState:
        """Create CTT state from predefined template."""
        # Templates like "research_and_summarize", "code_review", etc.
        pass
```

### 4.6 Enhanced State with Todo Integration

```python
class CTTTodoState(CTTState):
    """Extended CTT state with todo list compatibility."""
    
    # Add todo-specific fields
    todo_items: NotRequired[List[Dict]]  # TodoWrite format compatibility
    current_focus: NotRequired[str]    # Currently focused task_id
    active_branch: NotRequired[List[str]]  # Current execution path
    
    def to_todowrite_format(self) -> List[dict]:
        """Convert to Todowrite tool format."""
        return [
            {
                "content": f"{self._get_operator_symbol(t)}{task['title']}",
                "status": self._map_status(task["status"]),
                "priority": task.get("priority", 0),
            }
            for t in self.root_task_ids
            for t in self.tasks.values()
        ]
```

## 5. Implementation Priorities

### Phase 1: Core Types (✓ Done)
- `ctt_types.py` - Complete CTT type definitions

### Phase 2: Task Factory & Decomposition
- `ctt_factory.py` - Create tasks from templates/NL
- Add LLM decomposition prompt

### Phase 3: Execution Engine  
- `ctt_executor.py` - Implement operator handlers
- Add async execution for parallel tasks

### Phase 4: Todo Integration
- `ctt_todo_sync.py` - Sync with todo list
- Visual representation of operators

### Phase 5: Visualization
- `ctt_renderer.py` - Text/graphical tree display
- Progress tracking UI

## 6. File Structure Proposal

```
Lib/CTT/
├── __init__.py           # Exports
├── ctt_types.py          # Core types (exists)
├── ctt_factory.py       # Task creation
├── ctt_executor.py      # Execution engine
├── ctt_validation.py   # Tree validation
├── ctt_todo_sync.py    # Todo integration
├── ctt_renderer.py     # Visualization
└── ctt_prompts.py      # LLM prompts
```

## 7. Key Design Decisions

1. **Single async executor** vs **Process pool** - Use async for I/O-bound LLM calls
2. **Eager evaluation** vs **Lazy** - Eager for immediate feedback
3. **Flat todo list** vs **Nested tree** - Flat with indentation for now
4. **Strict validation** vs **Lenient** - Validate temporal consistency

## 8. References

- [W3C CTT Specification](https://www.w3.org/2012/02/ctt/)
- [CTTE Tool](http://giove.isti.cnr.it/tools/CTTE/)
- [Wikipedia: ConcurTaskTrees](https://en.wikipedia.org/wiki/ConcurTaskTrees)