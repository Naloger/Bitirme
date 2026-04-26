import uuid
import time
from pydantic import BaseModel, Field


class Page(BaseModel):
    """Temel Zettelkasten 'Page' Yapısı"""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)

    # Evergreen: Evrim takibi için oluşturulma ve güncellenme zamanları
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    raw_text: str = ""

    def touch(self):
        """Sayfa güncellendiğinde updated_at değerini tazeler."""
        self.updated_at = time.time()
