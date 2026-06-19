#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup script to pre-download and cache all required NLP models.

Run this script once to download all models to the persistent cache directory:
    python setup_models.py

Models will be cached in: ~/.cache/lemmatizer_models/ (customizable via LEMMATIZER_MODELS_DIR)

After running this, models won't be re-downloaded on subsequent runs.
"""

import sys
from pathlib import Path

from Libs.Lemmatizer.Models.model_cache import get_models_cache_dir

# Add services to path for imports
services_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(services_path))



def download_spacy_models():
    """Download spaCy models."""
    print("\n" + "="*70)
    print("DOWNLOADING SPACY MODELS")
    print("="*70 + "\n")

    try:
        from spacy.cli import download
        from Libs.Lemmatizer.Models.model_cache import is_spacy_model_available

        models = ["en_core_web_sm"]

        for model in models:
            if is_spacy_model_available(model):
                print(f"✓ spaCy model already cached: {model}\n")
                continue

            print(f"Downloading spaCy model: {model}")
            try:
                download(model)
                print(f"✓ Successfully downloaded {model}\n")
            except Exception as e:
                print(f"✗ Failed to download {model}: {e}\n")
                return False

        return True
    except ImportError:
        print("✗ spaCy not installed. Install with: pip install spacy")
        return False


def download_stanza_models():
    """Download Stanza models."""
    print("\n" + "="*70)
    print("DOWNLOADING STANZA MODELS")
    print("="*70 + "\n")

    try:
        import stanza
        from Libs.Lemmatizer.Models.model_cache import is_stanza_language_available

        languages = ["en", "tr"]  # English and Turkish

        for lang in languages:
            if is_stanza_language_available(lang):
                print(f"✓ Stanza model already cached: {lang}\n")
                continue

            print(f"Downloading Stanza model for: {lang}")
            try:
                stanza.download(lang, processors="tokenize,mwt,pos,lemma")
                print(f"✓ Successfully downloaded {lang}\n")
            except Exception as e:
                print(f"✗ Failed to download {lang}: {e}\n")
                return False

        return True
    except ImportError:
        print("✗ Stanza not installed. Install with: pip install stanza")
        return False


def main():
    """Main setup function."""

    print("\n" + "="*70)
    print("LEMMATIZER MODEL SETUP")
    print("="*70)

    # Setup caching (creates directories)
    cache_dir = get_models_cache_dir()
    print(f"\nModels will be cached in: {cache_dir}")

    # Download all models
    spacy_ok = download_spacy_models()
    stanza_ok = download_stanza_models()

    # Summary
    print("\n" + "="*70)
    print("SETUP SUMMARY")
    print("="*70)
    print(f"Cache directory: {cache_dir}")
    print(f"spaCy models: {'✓ Downloaded' if spacy_ok else '✗ Failed'}")
    print(f"Stanza models: {'✓ Downloaded' if stanza_ok else '✗ Failed'}")
    print("="*70 + "\n")

    if spacy_ok and stanza_ok:
        print("✓ All models downloaded successfully!")
        print("Models are cached and won't be re-downloaded.\n")
        return 0
    else:
        print("✗ Some models failed to download. Please check the errors above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

