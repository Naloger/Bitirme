from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date
from enum import Enum

class TaskStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    blocked = "blocked"
    cancelled = "cancelled"

class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class TaskNode(BaseModel):
    id: str = Field(..., description="Görevin benzersiz tanımlayıcısı (örn: TASK-001, EXP-APR-042)")
    title: str = Field(..., description="Kısa, eylem odaklı görev başlığı")
    description: Optional[str] = Field(None, description="Görevin detaylı açıklaması veya iş kuralı referansı")
    status: TaskStatus = Field(..., description="Görevin mevcut durumunu ifade eden enum değeri")
    priority: TaskPriority = Field(..., description="Öncelik seviyesini ifade eden enum değeri")
    assignee: Optional[str] = Field(None, description="Görevden sorumlu kullanıcı, rol veya departman")
    due_date: Optional[date] = Field(None, description="Son teslim tarihi (ISO 8601: YYYY-MM-DD)")
    dependencies: List[str] = Field(default_factory=list, description="Tamamlanması gereken bağımlı görev ID'leri")
    children: List[TaskNode] = Field(default_factory=list, description="Hiyerarşik alt görevlerin listesi")

    @field_validator("due_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

class TaskTree(BaseModel):
    """Kurumsal onay ve görev ağacının kök yapısı"""
    root_tasks: List[TaskNode] = Field(
        default_factory=list,
        description="Hiyerarşik görev ağacının en üst seviye görevleri"
    )
    metadata: Optional[dict] = Field(
        None,
        description="İsteğe bağlı meta veriler (örn: workflow_id, department, created_at)"
    )