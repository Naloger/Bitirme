from typing import TypedDict, List
from langchain_core.messages import SystemMessage, HumanMessage
import json

from support_lib.load_llm import load_llm
from Nodes.node_task_master_2.TodoDataType import (
    add_todo,
    list_todos,
    TodoList,
)

from langgraph.graph import StateGraph, END


# ------------------------------------------------------------------
# 1. Define the workflow state
# ------------------------------------------------------------------
class TodoWizardState(TypedDict):
    todo_list: TodoList
    user_request: str
    todos_to_add: List[dict] # Expected format: [{"title": "...", "description": "..."}, ...]
    current_index: int
    step: str                   # "ask_user", "generate_todos", "add_todos", "end"


# ------------------------------------------------------------------
# 2. Nodes
# ------------------------------------------------------------------
def node_ask_user(_state: TodoWizardState):
    print("\n=== Todo Generator ===")
    request = input("What do you want to do? (e.g., 'how to bake a cake', or 'q' to quit): ").strip()
    
    if request.lower() == 'q' or not request:
        return {"user_request": "", "step": "end"}
        
    return {"user_request": request, "step": "generate_todos"}


def node_generate_todos(state: TodoWizardState):
    request = state["user_request"]
    print(f"Generating steps for: '{request}'...")
    
    # Load LLM
    llm = load_llm()
    
    # Create prompt
    system_prompt = """You are a helpful assistant that breaks down a task into a series of actionable steps (todo items).
You MUST respond ONLY with a valid JSON array of objects.
Each object should have two string properties: "title" and "description".
Do NOT wrap the response in markdown code blocks (e.g. ```json). Do NOT add any introductory or concluding text.

Example output:
[
  {"title": "Step 1", "description": "Do the first thing"},
  {"title": "Step 2", "description": "Do the second thing"}
]"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Please create a step-by-step todo list for the following task: {request}")
    ]
    
    try:
        response = llm.invoke(messages)
        # Parse JSON
        content = str(response.content).strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        todos = json.loads(content.strip())
        print(f"Generated {len(todos)} steps.")
        return {"todos_to_add": todos, "current_index": 0, "step": "add_todos"}
    except Exception as e:
        print(f"Error generating or parsing todos: {e}")
        return {"todos_to_add": [], "current_index": 0, "step": "ask_user"}


def node_add_todos(state: TodoWizardState):
    todos = state["todos_to_add"]
    idx = state["current_index"]
    todo_list = state["todo_list"]
    
    if idx < len(todos):
        todo = todos[idx]
        title = todo.get("title", f"Step {idx+1}")
        desc = todo.get("description", "")
        
        add_todo(todo_list, title, desc)
        print(f"✅ Added: '{title}'")
        
        return {"current_index": idx + 1, "step": "add_todos"}
    
    return {"step": "ask_user"}


# ------------------------------------------------------------------
# 3. Routing functions
# ------------------------------------------------------------------
def route_step(state: TodoWizardState) -> str:
    step = state.get("step")
    if step == "end":
        return END
    elif step == "generate_todos":
        return "generate_todos"
    elif step == "add_todos":
        # Check if we have more to add
        if state.get("current_index", 0) < len(state.get("todos_to_add", [])):
            return "add_todos"
        else:
            return "ask_user"
    return "ask_user"


# ------------------------------------------------------------------
# 4. Build the graph
# ------------------------------------------------------------------
def build_wizard_graph():
    graph = StateGraph(TodoWizardState) # type: ignore

    graph.add_node("ask_user", node_ask_user) # type: ignore
    graph.add_node("generate_todos", node_generate_todos) # type: ignore
    graph.add_node("add_todos", node_add_todos) # type: ignore

    graph.set_entry_point("ask_user")

    graph.add_conditional_edges(
        "ask_user",
        route_step,
        {
            "generate_todos": "generate_todos",
            END: END,
        }
    )
    
    graph.add_edge("generate_todos", "add_todos")
    
    graph.add_conditional_edges(
        "add_todos",
        route_step,
        {
            "add_todos": "add_todos",
            "ask_user": "ask_user",
        }
    )

    return graph.compile()


# ------------------------------------------------------------------
# 5. The main runner
# ------------------------------------------------------------------
def run_todo_wizard(todo_list: TodoList):
    graph = build_wizard_graph()

    print("🧙 AI Todo Generator – tell me what to do and I'll create the steps!")
    initial_state = {
        "todo_list": todo_list,
        "user_request": "",
        "todos_to_add": [],
        "current_index": 0,
        "step": "ask_user"
    }

    graph.invoke(initial_state)

    print("\nAll done! Here is your current todo list:")
    print(list_todos(todo_list))


if __name__ == "__main__":
    my_todos = TodoList(name="My AI Generated Tasks")
    run_todo_wizard(my_todos)
