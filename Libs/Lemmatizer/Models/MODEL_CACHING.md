# Persistent Model Caching

This system automatically manages caching of NLP models so they're downloaded once and reused.

## Quick Start

### 1. First Time Setup (Download Models)

```bash
# Navigate to the services directory
cd C:\CalismaAlani\CodingPython\Bitirme\services

# Run the setup script to download all models
python services/Libs/Lemmatizer/setup_models.py
```

This downloads all required models to a persistent cache directory.

### 2. Use in Your Code

Models are now automatically loaded from cache on every run - no re-downloading!

```python
from services.Libs.Lemmatizer.lemma_matrix import build_cooccurrence_matrix

# Models are loaded from persistent cache
vectorizer, co_occurrence = build_cooccurrence_matrix(["Hello world", "Merhaba dünya"])
```

## Cache Location

By default, models are cached in: **`~/.cache/lemmatizer_models/`**

To customize this location, set the `LEMMATIZER_MODELS_DIR` environment variable:

```bash
# Windows PowerShell
$env:LEMMATIZER_MODELS_DIR = "C:\my\custom\path"

# Linux/Mac
export LEMMATIZER_MODELS_DIR=/path/to/models
```

## What Gets Cached

### spaCy Models (English)
- `en_core_web_sm` - English NLP model
- Cached in: `~/.cache/lemmatizer_models/spacy/`

### Stanza Models
- English (`en`) - Tokenization, POS tagging, lemmatization, MWT
- Turkish (`tr`) - Tokenization, POS tagging, lemmatization, MWT
- Multilingual - Language identification
- Cached in: `~/.cache/lemmatizer_models/stanza/`

## How It Works

1. **First Run**: When you use the lemmatizer for the first time after setup, models are loaded from the cache directory
2. **Subsequent Runs**: Models are loaded directly from cache (extremely fast)
3. **Automatic Caching**: Environment variables are automatically set to use persistent cache directories

## Adding New Languages

When you add a new language (e.g., `lemmatize_xlanguage`):

1. Create `LemmatizeByLanguage/lemmatize_xlanguage.py`
2. Add to `lemma_matrix.py`:
   ```python
   from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_xlanguage import lemmatize as lemmatize_xlanguage
   LANGUAGE_TO_LEMMATIZER["xl"] = lemmatize_xlanguage
   ```
3. If you need to pre-download the model, add to `setup_models.py`:
   ```python
   stanza.download("xl", processors="tokenize,mwt,pos,lemma")
   ```

## Troubleshooting

### Models not found after first setup?

Run the setup script again:
```bash
python services/Libs/Lemmatizer/setup_models.py
```

### Custom cache location not working?

Verify the environment variable:
```bash
# PowerShell
$env:LEMMATIZER_MODELS_DIR

# Linux/Mac
echo $LEMMATIZER_MODELS_DIR
```

### Want to see where cache is being used?

Check your active cache directory:

```python
from services.Libs.Lemmatizer.Models.model_cache import get_models_cache_dir

print(get_models_cache_dir())
```

## Performance Impact

After initial setup:
- **First script execution**: ~2-3 seconds (models loaded into memory)
- **Subsequent calls**: Microseconds (models cached in memory via `@lru_cache`)
- **Models are NOT re-downloaded** on each run

## Manual Model Download

If the setup script fails, you can download models manually:

```python
# spaCy
python -m spacy download en_core_web_sm

# Stanza
python -c "import stanza; stanza.download('en'); stanza.download('tr')"
```

Make sure `LEMMATIZER_MODELS_DIR` environment variable is set before downloading.

