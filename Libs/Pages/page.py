import uuid
import time
from dataclasses import dataclass, field


@dataclass
class Page:
    """Temel 'Page Yapısı'"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    creation_timestamp: float = field(default_factory=time.time)
    raw_text: str = ""
