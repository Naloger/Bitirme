from pydantic import BaseModel, Field
import httpx, json


class IntentResult(BaseModel):
    X: str
    K: str
    Y: str = Field(description="Mesaj sahibi")
    Z: str = Field(description="Çıkarımlar")
    T: str = Field(description="Beklenen tepki")


SYSTEM_PROMPT = """Sen bir niyet ayrıştırma uzmanısın.
Girdi: X (mesaj), K (bağlam, boş olabilir)
Çıktı: Yalnızca JSON → {"Y": "...", "Z": "...", "T": "..."}
Y: Mesaj sahibi (K'da varsa kullan, yoksa X'ten çıkar)
Z: Sahip hakkında bilgi/çıkarım (kesin olmayanları "olası" ile işaretle)
T: Beklenen tepki/aksiyon (bilgilendirme, müdahale, onay vb.)
Bilgi yoksa çıkarım yap; çıkarım da yapılamıyorsa "Belirlenemedi" yaz."""


def analyze(x: str, k: str = "", model: str = "gemma4:e4b", base_url: str = "http://localhost:11434") -> IntentResult:
    prompt = f"X: {x}" + (f"\nK: {k}" if k else "")

    resp = httpx.post(f"{base_url}/api/chat", json={
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        "stream": False,
    }, timeout=120)
    resp.raise_for_status()

    raw = resp.json()["message"]["content"]
    s, e = raw.find("{"), raw.rfind("}") + 1
    if s == -1 or e <= s:
        raise RuntimeError(f"JSON bulunamadı.\nYanıt: {raw}")

    data = json.loads(raw[s:e])
    return IntentResult(X=x, K=k, **data)


if __name__ == "__main__":
    result = analyze(
        x="Sistemdeki veritabanı yedeği alınamadı, disk kapasitesi %99 dolu! Acil destek gerekiyor!",
        k="Mesaj 'DB-Monitor-Bot' cron job'ından Slack üzerinden geldi. Sistem yöneticisi tatilde.",
    )
    for field, val in result.model_dump().items():
        print(f"{field}: {val}")