import uuid
from datetime import datetime
from typing import Optional

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
