import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class Todo(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def mark_completed(self):
        self.completed = True
        self.updated_at = datetime.now()


class TodoList(BaseModel):
    name: str = Field(..., min_length=1)
    todos: List[Todo] = Field(default_factory=list)

    def add_todo(self, todo: Todo):
        self.todos.append(todo)

    def remove_todo(self, todo_id: str):
        self.todos = [t for t in self.todos if t.id != todo_id]

    def get_todo(self, todo_id: str) -> Optional[Todo]:
        return next((t for t in self.todos if t.id == todo_id), None)

    def list_incomplete(self) -> List[Todo]:
        return [t for t in self.todos if not t.completed]


# ------------------------------------------------------------------
# 2. Tool functions (take todo_list as first argument)
# ------------------------------------------------------------------
def add_todo(todo_list: TodoList, title: str, description: Optional[str] = None) -> str:
    new_todo = Todo(title=title, description=description)
    todo_list.add_todo(new_todo)
    return f"Added todo: {title} (id: {new_todo.id})"


def complete_todo(todo_list: TodoList, todo_id: str) -> str:
    todo = todo_list.get_todo(todo_id)
    if not todo:
        return f"Todo with id {todo_id} not found."
    todo.mark_completed()
    return f"Marked '{todo.title}' as completed."


def remove_todo(todo_list: TodoList, todo_id: str) -> str:
    todo = todo_list.get_todo(todo_id)
    if not todo:
        return f"Todo with id {todo_id} not found."
    todo_list.remove_todo(todo_id)
    return f"Removed '{todo.title}'."


def list_todos(todo_list: TodoList) -> str:
    incomplete = todo_list.list_incomplete()
    if not incomplete:
        return "No pending todos. Great job!"
    return "Pending todos:\n" + "\n".join(f"- {t.title} (id: {t.id})" for t in incomplete)

