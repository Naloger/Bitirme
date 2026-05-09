from support_lib.Lemmatizer.lemmatize_english import lemmatize_english_text
from support_lib.Lemmatizer.lemmatize_turkish import lemmatize_turkish_text
from support_lib.Lemmatizer.segment_by_language import segment_by_language


def lemmatize_text(text: str) -> list[str]:
    """Lemmatize text by language using the shared support library."""
    lemmatized_lines: list[str] = []

    for segment in segment_by_language(text):
        seg_text = segment["text"]
        if segment["language"] == "tr":
            lemmatized_lines.extend(lemmatize_turkish_text(seg_text))
        else:
            lemmatized_lines.extend(lemmatize_english_text(seg_text))

    return lemmatized_lines
