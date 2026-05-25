import asyncio
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from services.Config import config as cfg

class SampleOutput(BaseModel):
    X: str = Field(
        description="Analiz edilen orijinal mesaj metni. Değiştirilmeden aktarılır."
    )
    K: str = Field(
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

SYSTEM_PROMPT = """Sen bir mesaj niyet ayrıştırma uzmanısın.
Teknik sistemlerden, kullanıcılardan veya botlardan gelen mesajları analiz ederek yapılandırılmış çıktı üretirsin.

Girdi:
  X — analiz edilecek ham mesaj
  K — ek bağlam (kaynak, ortam, kişi bilgisi; boş olabilir)

Çıktı kuralları:
  - Yalnızca tek bir JSON nesnesi döndür: {"Y": "...", "Z": "...", "T": "..."}
  - Markdown, açıklama veya ek metin ekleme.
  - Varsayım yapmak zorundaysan yap; belirsizliği her zaman "olası:" önekiyle işaretle.
  - Hiçbir çıkarım yapılamazsa ilgili alana "Belirlenemedi" yaz.

Alan kılavuzu:
  Y — Kaynağı belirle. K'ya öncelik ver; K boşsa X'teki ipuçlarını kullan.
  Z — Kaynak ve durum hakkında nesnel gözlemler. Birden fazlaysa "; " ile ayır.
  T — Tek cümle, gerekçeli aksiyon önerisi. Kategori: bilgilendirme | müdahale | onay | eskalasyon | göz ardı."""

_agent = Agent(
    model=OllamaModel(
        cfg.MODEL,
        provider=OllamaProvider(base_url=cfg.BASE_URL),
    ),
    system_prompt=SYSTEM_PROMPT,
    output_type=SampleOutput,
)


async def _analyze(x: str, k: str) -> SampleOutput:
    _prompt = f"X: {x}" + (f"\nK: {k}" if k else "")
    _result = await _agent.run(_prompt)
    _partial: SampleOutput = _result.output
    return SampleOutput(X=x, K=k, Y=_partial.Y, Z=_partial.Z, T=_partial.T)


def analyze(x: str, k: str = "") -> SampleOutput:
    return asyncio.run(_analyze(x, k))


if __name__ == "__main__":
    result = analyze(
        x="Sistemdeki veritabanı yedeği alınamadı, disk kapasitesi %99 dolu! Acil destek gerekiyor!",
        k="Mesaj 'DB-Monitor-Bot' cron job'ından Slack üzerinden geldi. Sistem yöneticisi tatilde.",
    )
    for field, val in result.model_dump().items():
        print(f"{field}: {val}")
