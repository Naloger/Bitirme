from typing import List, Optional

from pydantic import BaseModel, Field

from Agents.Nodes.node_task_master.Classes.Todo import Todo


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
