# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

import stanza

from services.Libs.Lemmatizer.Models.model_cache import (
    print_model_setup_instructions,
)


# ---------------------------------------------------------------------------
# Optional Zemberek (Java) integration
# ---------------------------------------------------------------------------
def _load_zemberek() -> Any | None:
    try:
        zemberek_mod = importlib.import_module("zemberek")
    except ImportError:
        return None

    TurkishMorphology = getattr(zemberek_mod, "TurkishMorphology", None)
    if TurkishMorphology is None:
        return None

    create_with_defaults = getattr(TurkishMorphology, "create_with_defaults", None)
    if not callable(create_with_defaults):
        return None

    try:
        return create_with_defaults()
    except (AttributeError, LookupError, OSError, RuntimeError, TypeError, ValueError):
        return None


_zemberek: Any | None = _load_zemberek()

# ---------------------------------------------------------------------------
# Stanza pipeline
# ---------------------------------------------------------------------------
def _load_stanza_turkish() -> Any | None:
    """Load the Stanza Turkish pipeline with persistent caching.

    Models are cached persistently in LEMMATIZER_MODELS_DIR (~/.cache/lemmatizer_models/ by default).
    On first use, models are automatically downloaded to the cache directory.

    Returns:
        Stanza pipeline if available, None otherwise
    """
    try:
        return stanza.Pipeline(
            lang="tr",
            processors="tokenize,mwt,pos,lemma",
            use_gpu=True,
            verbose=False,
        )
    except (OSError, ValueError) as exc:
        print_model_setup_instructions()
        print("To download Turkish Stanza model, run:")
        print("  python -c \"import stanza; stanza.download('tr')\"")
        return None

_stanza_tr = _load_stanza_turkish()


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

_LETTER_RE = re.compile(r"[^a-zçğıöşüA-ZÇĞİÖŞÜ'-]")


def _clean_token(tok: str) -> str:
    """Keep only Turkish/ASCII letters and basic punctuation (dash/apostrophe)."""
    return _LETTER_RE.sub("", tok.strip().lower())


def _strip_infinitive(lemma: str) -> str:
    """koşmak → koş  (strip -mak / -mek infinitive suffix)."""
    if lemma.endswith(("mak", "mek")):
        return lemma[:-3]
    return lemma


def _strip_plural(lemma: str) -> str:
    """Strip the most common Turkish plural suffixes (longest match first)."""
    for suf in ("ların", "lerin", "ları", "leri", "lar", "ler"):
        if lemma.endswith(suf) and len(lemma) > len(suf) + 1:
            return lemma[: -len(suf)]
    return lemma


def _normalize_candidate(candidate: object | bytes | None) -> str:
    """Clean a stem/lemma string coming from Zemberek.

    - Decodes bytes, repairs common mojibake, normalizes to NFC.
    - Strips Zemberek '+Verb+...' annotation tails.
    Returns an empty string on any failure.
    """
    if candidate is None:
        return ""

    try:
        if isinstance(candidate, bytes):
            candidate = candidate.decode("utf-8", errors="ignore")
        candidate_text = str(candidate).strip()

        # Attempt latin1→utf-8 mojibake repair
        if any(marker in candidate_text for marker in ("Ã", "Å", "Â")):
            repaired = candidate_text.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
            if repaired:
                candidate_text = repaired

        candidate_text = unicodedata.normalize("NFC", candidate_text)
        return candidate_text.split("+", 1)[0].strip()
    except (AttributeError, LookupError, TypeError, UnicodeError, ValueError):
        return ""


def _infer_pos(source: str) -> str | None:
    """Infer a coarse POS tag (VERB / NOUN / PROPN) from a free-form string."""
    low = source.lower()
    if "verb" in low:
        return "VERB"
    if "prop" in low or "proper" in low:
        return "PROPN"
    if "noun" in low:
        return "NOUN"
    return None


def _candidate_is_plausible(candidate: str, source: str, stanza_lemma: str) -> bool:
    """Reject obviously broken Zemberek outputs.

    We keep a candidate only if it has a reasonable edit-similarity to the
    original token or the Stanza lemma. This filters fragments such as
    single letters, mojibake leftovers, or unrelated words.
    """
    candidate = _clean_token(candidate)
    source = _clean_token(source)
    stanza_lemma = _clean_token(stanza_lemma)

    if len(candidate) < 2:
        return False

    if candidate in {source, stanza_lemma}:
        return True

    if candidate in source or candidate in stanza_lemma:
        return True

    def _longest_common_substring(a: str, b: str) -> int:
        if not a or not b:
            return 0
        return SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b)).size

    def _ratio(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    common = max(_longest_common_substring(candidate, source), _longest_common_substring(candidate, stanza_lemma))
    return common >= 3 or max(_ratio(candidate, source), _ratio(candidate, stanza_lemma)) >= 0.6


# ---------------------------------------------------------------------------
# Simple fallback (no Stanza)
# ---------------------------------------------------------------------------

def _simple_split(text: str) -> list[str]:
    """Whitespace-split + basic lemmatisation when Stanza is unavailable."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in text.split():
        tok = _clean_token(raw)
        tok = _strip_infinitive(tok)
        tok = _strip_plural(tok)
        if tok and tok not in seen:
            seen.add(tok)
            result.append(tok)
    return result


# ---------------------------------------------------------------------------
# Zemberek stem extraction
# ---------------------------------------------------------------------------

_ZEMBEREK_STEM_ATTRS = ("getStem", "stem", "getRoot", "root", "lemma", "getLemma", "getLemmas", "lemmas")
_ZEMBEREK_POS_ATTRS  = ("getPos", "pos", "getType", "type")


def _zemberek_stem(word: str) -> tuple[str | None, str | None]:
    """Return (stem, pos_hint) from Zemberek, or (None, None) on failure."""
    if _zemberek is None:
        return None, None
    try:
        analyses = _zemberek.analyze(word)
    except (AttributeError, LookupError, RuntimeError, TypeError, ValueError):
        return word.lower(), None

    try:
        if not analyses:
            return word.lower(), None

        a0 = analyses[0]

        # --- stem ---
        stem: str | None = None
        for attr in _ZEMBEREK_STEM_ATTRS:
            val = getattr(a0, attr, None)
            if val is None:
                continue
            try:
                out = val() if callable(val) else val
            except (AttributeError, TypeError, ValueError):
                continue
            if not out:
                continue
            candidate = _normalize_candidate(out[0] if isinstance(out, (list, tuple)) else out)
            clean = _clean_token(candidate)
            if _candidate_is_plausible(clean, word, word):
                stem = clean
                break
        if stem is None:
            stem = _clean_token(_normalize_candidate(a0))
            if not _candidate_is_plausible(stem or "", word, word):
                stem = None

        # --- pos ---
        pos: str | None = None
        for attr in _ZEMBEREK_POS_ATTRS:
            val = getattr(a0, attr, None)
            if val is None:
                continue
            try:
                p = val() if callable(val) else val
            except (AttributeError, TypeError, ValueError):
                continue
            pos = _infer_pos(_normalize_candidate(p))
            if pos:
                break
        if pos is None:
            pos = _infer_pos(_normalize_candidate(a0))

        return stem, pos
    except (AttributeError, IndexError, LookupError, RuntimeError, TypeError, ValueError):
        return word.lower(), None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lemmatize(text: str) -> list[str]:
    """Lemmatize Turkish *text* and return a deduplicated list of stems.

    Pipeline:
      1. Stanza for tokenisation, POS tagging, and base lemmas.
      2. Zemberek (optional) for improved stem extraction per token.
      3. Post-processing: strip infinitive / plural suffixes, deduplicate.

    Falls back to simple whitespace splitting when Stanza is unavailable.
    """
    if not text:
        return []

    if _stanza_tr is None:
        return _simple_split(text)

    try:
        doc = _stanza_tr(text)
    except (AttributeError, LookupError, OSError, RuntimeError, TypeError, ValueError):
        return _simple_split(text)

    seen: set[str] = set()
    result: list[str] = []

    for sent in doc.sentences:
        for word in sent.words:
            if not word.text or word.upos == "PUNCT":
                continue

            raw_text   = word.text.strip()
            # Skip numeric / one-character fragments early; these are common
            # sources of broken stems like "ağu" / "trilyon" in some runtimes.
            if any(ch.isdigit() for ch in raw_text) or len(raw_text) < 2:
                continue

            stanza_lemma = (word.lemma or raw_text).lower().strip()

            # Try Zemberek first; fall back to Stanza lemma
            stem, pos_hint = _zemberek_stem(raw_text)
            if not _candidate_is_plausible(stem or "", raw_text, stanza_lemma):
                stem = _clean_token(stanza_lemma)

            if not stem:
                continue

            # Resolve POS from Stanza when Zemberek didn't provide one
            if pos_hint is None and word.upos:
                pos_hint = _infer_pos(word.upos)

            # Apply suffix stripping based on POS
            if pos_hint == "VERB":
                stem = _strip_infinitive(stem)
            elif pos_hint in ("NOUN", "PROPN"):
                stem = _strip_plural(stem)
            else:
                stem = _strip_plural(_strip_infinitive(stem))

            # Final safety net: if the reduced output became too short or no longer
            # resembles the source/Stanza lemma, fall back to the Stanza lemma.
            if not _candidate_is_plausible(stem, raw_text, stanza_lemma):
                fallback = _clean_token(stanza_lemma)
                if _candidate_is_plausible(fallback, raw_text, stanza_lemma):
                    stem = fallback
                else:
                    continue

            if stem and stem not in seen:
                seen.add(stem)
                result.append(stem)

    return result
