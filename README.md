Project-scoped spaCy model kurulumu (otomatik):
# DesignProject

Amaç: `Instructions.md` içeriğine göre proje klasörleri ve örnek NLP nodeları oluşturmak — lemmatizer, metin grafu vb.

## Kurulum (PowerShell) — ÖNERİLEN YÖL

Proje kökünde hazır bir PowerShell betiği var: `scripts\install_spacy_models.ps1` 

**1. Dry-run (yapılacakları göster):**
```powershell
.\scripts\install_spacy_models.ps1
```

**2. Kurulum çalıştır:**
```powershell
.\scripts\install_spacy_models.ps1 -Install
```

Bu betik:
- `.venv` sanal ortamını oluşturur
- spacy, stanza, nltk kurulur
- spaCy modelleri indirilir (en_core_web_sm)
- Stanza Türkçe modeli indirilir
- NLTK veri paketleri indirilir (wordnet, omw, punkt)

**3. Sanal ortamı aktif et:**
```powershell
.\.venv\Scripts\Activate.ps1
```

## Çalıştırma örnekleri

Venv aktif ettikten sonra:

```powershell
# Node listesini gör
python main.py list

# Tek node çalıştır
python main.py run --node lemmatize

# Birden fazla node çalıştır
python main.py run --nodes lemmatize,graph

# Tüm nodeları çalıştır
python main.py run --all

# Stream Guard nodunu çalıştır (Ollama gerekir)
python Agents/Nodes/node_stream_guard/node.py
```

## Ortam yapısı

```
DesignProject/
├── .venv/               # Sanal ortam (spacy, stanza, nltk, torch)
├── Agents/
│   ├── Nodes/
│   │   ├── node_lemmatizer/    # Türkçe/İngilizce lemmatizer
│   │   ├── node_textgraph/     # Metin grafu oluşturucu
│   ├── Prompts/
│   ├── Tools/
├── scripts/
│   ├── install_spacy_models.ps1
│   ├── install_models.py
├── TUI/
├── requirements.txt
├── main.py
└── README.md
```

## Notlar

- Lemmatizer, spaCy, Stanza veya NLTK kullanarak lemmatizasyon yapar
- Türkçe için Stanza tercih edilir
- İngilizce için spaCy + NLTK tercih edilir
- Tüm modeller `.venv` içinde yerel olarak depolanır
- **Stream Guard Node** (node_stream_guard) üretken modellerin sonsuz döngüsünü algılar ve engeller:
  - Loop detection: Tekrarlı chunk'ları algılar
  - Thinking capture: Model içsel düşüncesini kaydeder
  - Auto-restart: Döngüye girse bile geri kurtarır (max 2 deneme)
