from typing import Optional

from pydantic import BaseModel, Field


class IntentAnalysisOutput(BaseModel):
    sender_identity: str = Field(
        description=(
            "Mesajı gönderen kişi, sistem veya bot. "
            "Öncelikle bağlam bilgisinden (context_info) çıkarılır; bağlam bilgisi yoksa ham mesajdaki (message_text) ipuçlarına göre tahmin edilir. "
            "Bulunamıyorsa 'kullanıcı', 'sistem' veya 'bot' olarak tahmin et. Belirlenemiyorsa 'Belirlenemedi' yaz."
        )
    )
    inferences: str = Field(
        description=(
            "Mesaj sahibi ve mevcut durum hakkında yapılan durumsal çıkarımlar ve nesnel gözlemler. "
            "Örnek: 'kullanıcı selamlama yaptı' veya 'olası: disk yetersizliği'. "
            "Birden fazla çıkarım varsa '; ' ile ayır. Hiçbir çıkarım yapılamazsa 'Belirlenemedi' yaz."
        )
    )
    recommended_action: str = Field(
        description=(
            "Duruma uygun aksiyon önerisi. "
            "Kategori ön ekiyle birlikte tek bir cümle halinde yazılmalıdır. "
            "Format: [kategori] - [Gerekçe ve aksiyon açıklaması]. "
            "Kategori şunlardan biri olmalıdır: bilgilendirme | müdahale | onay | eskalasyon | göz ardı. "
            "Örnek: 'bilgilendirme - Kullanıcı selamlandı, sohbete devam edilebilir.'"
        )
    )


class IntentResult(IntentAnalysisOutput):
    message_text: str = Field(
        default="",
        description="Analiz edilen orijinal ham mesaj metni. Değiştirilmeden aynen aktarılır."
    )
    context_info: str = Field(
        default="",
        description="Mesajla birlikte sağlanan ek bağlam bilgisi (kaynak sistem, kanal, kişi vb.). Sağlanmadıysa boş kalır."
    )


class IntentAgentState(BaseModel):
    """The state payload carrying context and progress through the IntentAgent pipeline."""
    message_text: str
    context_info: str
    analysis_result: Optional[IntentResult] = None
    error: Optional[str] = None


