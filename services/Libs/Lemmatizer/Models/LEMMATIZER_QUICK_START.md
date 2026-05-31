# Quick Start: Persistent Model Caching

## Step 1: Download Models (One Time Only)

```bash
cd C:\CalismaAlani\CodingPython\Bitirme\services
python services/Libs/Lemmatizer/setup_models.py
```

This downloads all NLP models and caches them permanently in `~/.cache/lemmatizer_models/`

## Step 2: Use Normally

```python
from services.Libs.Lemmatizer.lemma_matrix import build_cooccurrence_matrix

# Models are loaded from cache - fast and no re-downloads!
vectorizer, co_occurrence = build_cooccurrence_matrix(
    ["The cats chase mice.", "Kedi fareyi kovalıyor."]
)
```

## How It Works

| Time | Action | Speed |
|------|--------|-------|
| First run | Setup script downloads models to persistent cache | ~5 mins |
| Second run | Models loaded from disk into memory | ~2-3 secs |
| Third+ run | Models cached in memory (super fast) | microseconds |

## Key Benefits

✅ **No Re-downloads**: Models cached permanently  
✅ **Fast Startup**: Models only loaded once per script  
✅ **Flexible Location**: Customize cache via `LEMMATIZER_MODELS_DIR` env var  
✅ **Clean Code**: Caching is automatic, no code changes needed  

## Cache Contents

```
~/.cache/lemmatizer_models/
├── spacy/
│   └── en_core_web_sm/          # English model (400MB)
└── stanza/
    ├── en/                       # English language models
    └── tr/                       # Turkish language models
```

Total size: ~1-2 GB (one-time download)

## Troubleshooting

**"Model not found" error?**
```bash
python services/Libs/Lemmatizer/setup_models.py
```

**Want to use a different cache location?**
```bash
# PowerShell
$env:LEMMATIZER_MODELS_DIR = "D:\my_models"

# Then run your Python code - it will use D:\my_models
```

**Check current cache location:**

```python
from services.Libs.Lemmatizer.Models.model_cache import get_models_cache_dir

print(get_models_cache_dir())
```

---

That's it! 🎉 Models are now cached and won't be re-downloaded.

