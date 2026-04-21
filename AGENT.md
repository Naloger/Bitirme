# AGENT.md

Bu belge, bu repoda calisan insan veya AI coding agent'lari icin operasyon kurallarini tanimlar.

## 1) Amac ve Kapsam

- Hedef: `DesignProject` icindeki node tabanli NLP/LLM akislarini guvenli ve izlenebilir sekilde gelistirmek.
- Kapsam: Kod degisikligi, test, dokumantasyon, konfigurasyon guncellemeleri.
- Kapsam disi: Uretim sirri/paylasilmamasi gereken anahtarlarin repoya yazilmasi.

## 2) Proje Baglami (Kisa)

- Giris noktasi: `main.py` (su an `TUI/tui_app.py` icindeki no-op calisiyor).
- Kritik node: `Agents/Nodes/node_task_master/node_TaskMaster.py`.
- CTT tipleri/validasyon: `Lib/CTT/ctt_types.py`.
- LLM ayari: `llm_config.json` + `llm_config.py`.

## 3) Calisma Kurallari

- Kucuk ve amac odakli commit/degisiklik yap.
- Var olan dosya stilini koru (isimlendirme, import duzeni, hata yonetimi).
- Gerekmedikce buyuk capli refactor yapma.
- Hata mesajlarini eyleme donuk yaz (ne bozuk + nasil duzelir).

## 4) Guvenlik ve Gizlilik

- `llm_config.json` icine gercek API anahtari ekleme.
- Lokal URL/model bilgisi disinda hassas veri tutma.
- Input/Output orneklerinde PII veya gizli icerik kullanma.
- Harici servise gonderilen metnin loglanmasinda minimum veri prensibini uygula.

## 5) Degisiklik Prensipleri

- Node degisikliginde mümkünse:
  - `Input.txt` ve `Output.txt` orneklerini guncelle.
  - Ilgili testleri ekle/guncelle.
- `llm_config.py` degisirse hata senaryolari (`tests/test_config_*`) korunmali.
- CTT uretimi degisirse `validate_ctt_tree` uyumlulugu korunmali.

## 6) Kurulum ve Calistirma (PowerShell)

```powershell
.\scripts\install_spacy_models.ps1
.\scripts\install_spacy_models.ps1 -Install
.\.venv\Scripts\Activate.ps1
```

```powershell
python main.py
python Agents/Nodes/node_task_master/node_TaskMaster.py
python Agents/Nodes/node_stream_guard/node_LoopGuard.py
```

## 7) Test ve Dogrulama

```powershell
python -m pytest -q
```

Alternatif (script tabanli hizli kontrol):

```powershell
python tests/test_taskmaster_debug.py
```

## 8) Done Kriterleri

- Kod calisiyor ve temel testler geciyor.
- Dokumantasyon (gerekiyorsa `README.md`, bu dosya, ilgili node aciklamasi) guncel.
- Geriye donuk davranis bozulmasi yok veya net sekilde not edildi.

