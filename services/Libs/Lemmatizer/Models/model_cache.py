# -*- coding: utf-8 -*-
"""Persistent model caching for Stanza and spaCy models.

This module manages downloading and caching NLP models to a permanent
directory so they don't need to be re-downloaded on each run.

Set the LEMMATIZER_MODELS_DIR environment variable to customize the cache location:
    export LEMMATIZER_MODELS_DIR=/path/to/models

Default location: ~/.cache/lemmatizer_models/
"""

from __future__ import annotations

import os
from pathlib import Path

# ============================================================================
# Cache Directory Management
# ============================================================================

def get_models_cache_dir() -> Path:
    """Get the persistent models cache directory.

    Priority:
        1. LEMMATIZER_MODELS_DIR environment variable
        2. Default: ~/.cache/lemmatizer_models/

    Returns:
        Path object pointing to the cache directory (created if needed)
    """
    # Check for explicit environment variable
    env_cache = os.environ.get("LEMMATIZER_MODELS_DIR")
    if env_cache:
        cache_dir = Path(env_cache).expanduser().resolve()
    else:
        # Default to user cache directory
        cache_dir = Path.home() / ".cache" / "lemmatizer_models"

    # Create directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def setup_model_caching() -> None:
    """Configure environment variables for persistent model caching.

    Sets up:
        - STANZA_RESOURCES_DIR: Directory for Stanza models
        - SPACY_HOME: Directory for spaCy models

    This ensures models are downloaded to the persistent cache directory
    instead of temporary locations.
    """
    cache_dir = get_models_cache_dir()

    # Set Stanza cache directory
    stanza_dir = cache_dir / "stanza"
    os.environ["STANZA_RESOURCES_DIR"] = str(stanza_dir)
    stanza_dir.mkdir(parents=True, exist_ok=True)

    # Set spaCy cache directory
    spacy_dir = cache_dir / "spacy"
    os.environ["SPACY_HOME"] = str(spacy_dir)
    spacy_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Model Availability Check
# ============================================================================

def is_spacy_model_available(model_name: str) -> bool:
    """Check if a spaCy model is already cached.

    Args:
        model_name: spaCy model name (e.g., 'en_core_web_sm')

    Returns:
        True if model is cached, False otherwise
    """
    cache_dir = get_models_cache_dir() / "spacy"
    model_dir = cache_dir / model_name
    return model_dir.exists() and (model_dir / "meta.json").exists()


def is_stanza_language_available(lang: str) -> bool:
    """Check if a Stanza language model is already cached.

    Args:
        lang: Language code (e.g., 'en', 'tr')

    Returns:
        True if language model is cached, False otherwise
    """
    cache_dir = get_models_cache_dir() / "stanza" / lang
    # Stanza stores models in language-specific directories
    return cache_dir.exists() and any(cache_dir.iterdir())


# ============================================================================
# Model Download Instructions
# ============================================================================

def print_model_setup_instructions() -> None:
    """Print instructions for downloading required models."""
    cache_dir = get_models_cache_dir()
    print("\n" + "=" * 70)
    print("MODEL SETUP REQUIRED")
    print("=" * 70)
    print(f"\nModels will be cached in: {cache_dir}\n")
    print("Run the following commands to download all required models:\n")
    print("  # Download spaCy English model")
    print("  python -m spacy download en_core_web_sm\n")
    print("  # Download Stanza models (when you first use them)")
    print("  # English: python -c \"import stanza; stanza.download('en')\"")
    print("  # Turkish: python -c \"import stanza; stanza.download('tr')\"")
    print("\n" + "=" * 70 + "\n")


# Initialize caching on import
setup_model_caching()

