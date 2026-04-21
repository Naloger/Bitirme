# PROJECT.md

## Proje Ozeti

`DesignProject`, node-temelli bir NLP/LLM deneme ve gelistirme alanidir.
Temel hedef, metin isleme ve gorev planlama adimlarini moduler node'lar halinde calistirmaktir.

## Hedefler

- Metin isleme node'larini tekil ve coklu senaryoda calistirmak.
- Ollama tabanli planlama/uretim node'larini standart bir konfigurasyonla yonetmek.
- CTT (ConcurTaskTrees) uyumlu gorev agaci ciktisi uretmek ve dogrulamak.

## Mimari Genel Bakis

- `main.py` -> `TUI/tui_app.py` giris akisi (su an TUI no-op).
- `Agents/Nodes/` -> Calistirilabilir node modulleri:
  - `node_lemmatizer`
  - `node_textgraph`
  - `node_stream_guard`
  - `node_task_master`
- `Lib/CTT/` -> CTT tipleri ve validasyon.
- `Data/` -> veri tipleri/archetype/persona yapilari.
- `scripts/` -> kurulum ve model indirme scriptleri.

## Klasor Yapisi (Kritik)

- `Agents/Nodes/`: Node implementasyonlari ve ornek `Input.txt` / `Output.txt`.
- `Lib/CTT/`: CTT semasi, tipler, validasyon yardimcilari.
- `TUI/`: Kullanici giris katmani (gecici olarak devre disi mesajli).
- `tests/`: Konfigurasyon ve task master odakli test/dogrulamalar.
- `llm_config.json`: Ollama ve loop-guard calisma parametreleri.

## Temel Akislar

1. Konfigurasyon yuklenir (`llm_config.py`).
2. Node input'u alinip model cagrisi yapilir (gereken node'larda).
3. Cikti parse edilir; gerekiyorsa CTT validasyonu uygulanir.
4. Sonuc `Output.txt` veya stdout uzerinden raporlanir.

## Bagimliliklar

`requirements.txt` dosyasinda tanimli ana paketler:

- `langgraph`, `langchain`
- `pydantic`
- `spacy`, `stanza`, `nltk`
- `textual`, `fastmcp`, `langdetect`

## Kurulum ve Calistirma (PowerShell)

```powershell
.\scripts\install_spacy_models.ps1 -Install
.\.venv\Scripts\Activate.ps1
```

```powershell
python main.py
python Agents/Nodes/node_task_master/node_TaskMaster.py
```

## Konfigurasyon

- Dosya: `llm_config.json`
- Zorunlu alanlar:
  - `provider` (su an sadece `ollama`)
  - `ollama.model`
  - `ollama.base_url`
- Loop guard davranisi `loop_guard` altindaki alanlarla ayarlanir.

## Test Stratejisi

- Birim/regresyon testleri: `tests/test_config_loading.py`, `tests/test_config_errors.py`
- Node davranis kontrolu: `tests/test_taskmaster_debug.py`

Ornek:

```powershell
python -m pytest -q
```

## Gelistirme Notlari

- Yeni node eklerken ilgili klasorde `Input.txt` ve `Output.txt` kalibini koruyun.
- LLM ciktilarinda JSON parse edilmesi gereken yerlerde acik hata mesaji verin.
- CTT uyumlulugunu bozan degisiklikleri `Lib/CTT` ile birlikte ele alin.

## Kisa Yol Haritasi

- TUI tekrar etkinlestirme ve node secim arayuzu.
- Node bazli standart test fixture'lari.
- Konfigurasyon sema dogrulamasi ve daha detayli hata raporlama.

