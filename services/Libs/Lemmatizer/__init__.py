# -*- coding: utf-8 -*-
"""Lemmatizer package with persistent model caching.

Models are automatically cached to avoid re-downloads.
Default cache location: ~/.cache/lemmatizer_models/

Customize cache location:
    import os
    os.environ['LEMMATIZER_MODELS_DIR'] = '/path/to/cache'

First time setup (download all models):
    python services/Libs/Lemmatizer/setup_models.py

For detailed information, see: MODEL_CACHING.md
"""

# Auto-initialize model caching on import
from services.Libs.Lemmatizer.Models.model_cache import setup_model_caching

setup_model_caching()

__all__ = ["setup_model_caching"]

