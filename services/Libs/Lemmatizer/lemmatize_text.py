
import re

from services.Libs.Lemmatizer.LanguageSegmentation.segment_by_language import (
    segment_by_language,
)
from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_english import (
    lemmatize as lemmatize_english,
)
from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_turkish import (
    lemmatize as lemmatize_turkish,
)

_TURKISH_HINT_RE = re.compile(r"[çğıöşüÇĞİÖŞÜ]")


def _pick_lemmatizer(language: str | None, text: str):
    """Select a lemmatizer, falling back to a simple Turkish/English heuristic."""
    lang = (language or "").strip().lower()
    if lang == "tr":
        return lemmatize_turkish
    if lang == "en":
        return lemmatize_english
    if _TURKISH_HINT_RE.search(text):
        return lemmatize_turkish
    return lemmatize_english


def lemmatize_text(text: str) -> str:
    """Lemmatize mixed-language text and return a single normalized string."""
    lemmatized_segments: list[str] = []

    for segment in segment_by_language(text):
        seg_text = segment["text"]
        language = segment.get("language")
        lemmas = _pick_lemmatizer(language, seg_text)(seg_text)

        if lemmas:
            lemmatized_segments.append(" ".join(lemmas))

    return " ".join(lemmatized_segments)
