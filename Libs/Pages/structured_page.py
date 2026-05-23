import time
from dataclasses import dataclass, field
from typing import List, Tuple

from Libs.Pages.page import Page


@dataclass
class StructuredPage(Page):
    """
    Organize edilmiş bilgi temsili.
    Kelimeler arası yapısal ilişkileri zamanla ve kumulatif olarak
    toplamak suretiyle oluşturulur.
    """

    triplets: List[Tuple[str, int , str]] = field(default_factory=list)
    structured_at: float = field(default_factory=time.time)
