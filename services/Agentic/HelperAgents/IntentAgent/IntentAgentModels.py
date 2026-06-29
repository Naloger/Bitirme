from typing import Optional

from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    X: str = Field(
        default="",
        description="Analiz edilen orijinal mesaj metni. Değiştirilmeden aktarılır."
    )
    K: str = Field(
        default="",
        description="Mesajla birlikte sağlanan bağlam bilgisi (kaynak sistem, kanal, kişi vb.). Sağlanmadıysa boş string."
    )
    Y: str = Field(
        description=(
            "Mesajı gönderen kişi, sistem veya bot. "
            "Önce K'dan çıkar; K yoksa X'teki ipuçlarına göre tahmin et. "
            "Belirlenemiyorsa 'Belirlenemedi' yaz."
        )
    )
    Z: str = Field(
        description=(
            "Mesaj sahibi ve mevcut durum hakkında çıkarımlar. "
            "Kesin olmayan bilgileri 'olası:' önekiyle işaretle. "
            "Birden fazla çıkarım varsa '; ' ile ayır. "
            "Hiçbir çıkarım yapılamazsa 'Belirlenemedi' yaz."
        )
    )
    T: str = Field(
        description=(
            "Duruma uygun önerilen aksiyon. "
            "Şu kategorilerden birini seç: bilgilendirme | müdahale | onay | eskalasyon | göz ardı. "
            "Kısa gerekçesiyle birlikte tek cümle yaz."
        )
    )

class IntentAgentState(BaseModel):
    """The state payload carrying context and progress through the IntentAgent pipeline."""
    message_text: str  # X
    context_info: str  # K
    analysis_result: Optional[IntentResult]
    error: Optional[str]
