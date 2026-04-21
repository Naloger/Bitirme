from pathlib import Path
import re
from typing import Any, cast
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

# Import langdetect exception for specific handling
try:
    from langdetect.lang_detect_exception import LangDetectException
except ImportError:
    LangDetectException = Exception  # Fallback


BASE = Path(__file__).parent
INPUT = BASE / "Input.txt"
OUTPUT = BASE / "Output.txt"


# Check dependencies at module load time and set to None if not available, allowing graceful degradation.
# Optional dependencies
detect = None
try:
    from langdetect import detect
except ImportError:
    detect = None

spacy_en = None
try:
    import spacy
    spacy_en = spacy.load("en_core_web_sm")
except (ImportError, OSError):
    spacy_en = None

stanza_tr = None
try:
    import stanza
    stanza_tr = stanza.Pipeline(
        lang="tr", processors="tokenize,mwt,pos,lemma", use_gpu=False, verbose=False
    )
except (ImportError, RuntimeError):
    try:
        stanza.download("tr")
        stanza_tr = stanza.Pipeline(
            lang="tr", processors="tokenize,mwt,pos,lemma", use_gpu=False, verbose=False
        )
    except (ImportError, RuntimeError):
        stanza_tr = None

WordNetLemmatizer = None
nltk_available = False
try:
    from nltk.stem import WordNetLemmatizer
    nltk_available = True
except ImportError:
    WordNetLemmatizer = None
    nltk_available = False


# Program

class LemmatizerState(TypedDict, total=False):
    text: str
    lemmatized_lines: list[str]
    error: str

def _detect_sentence_language(sentence: str) -> str:
    """Detect language: Turkish if special chars found, else English."""
    if re.search(r"[çğıöşüÇĞİÖŞÜ]", sentence):
        return "tr"
    if detect:
        try:
            detected = detect(sentence)
            return "tr" if detected.startswith("tr") else "en"
        except LangDetectException:
            pass
    return "en"


def _lemmatize_text(text: str) -> list[str]:
    # Split by sentence boundaries and common punctuation
    sentences = re.split(r'\n.!?;:,—-""\'\'"+', text)
    lemmatized_lines: list[str] = []

    for sentence in sentences:
        # Clean whitespace and remaining punctuation from edges
        cleaned_sentence = sentence.strip().rstrip('.,!?;:\'"—-')
        if not cleaned_sentence:
            continue

        sent_lang = _detect_sentence_language(cleaned_sentence)
        lemma_words: list[str] = []

        if sent_lang == "en" and spacy_en is not None:
            doc = spacy_en(cleaned_sentence)
            lemma_words = [token.lemma_.lower() for token in doc if token.text.strip()]
        elif sent_lang == "tr" and stanza_tr is not None:
            try:
                tr_doc = stanza_tr(cleaned_sentence)
                for sent_obj in tr_doc.sentences:
                    for word in sent_obj.words:
                        lemma = str(getattr(word, "lemma", word.text)).lower()
                        # Remove punctuation from lemma
                        lemma = lemma.strip().rstrip('.,!?;:\'"—-')
                        if lemma:
                            lemma_words.append(lemma)
            except RuntimeError:
                pass

        if not lemma_words and sent_lang == "en" and nltk_available and WordNetLemmatizer:
            words = re.findall(r"\w+", cleaned_sentence, flags=re.UNICODE)
            lemmatizer = WordNetLemmatizer()
            for word in words:
                normalized = word.lower()
                lemma_verb = lemmatizer.lemmatize(normalized, pos="v")
                lemma_words.append(
                    lemma_verb if lemma_verb != normalized else lemmatizer.lemmatize(normalized, pos="n")
                )

        if not lemma_words:
            words = re.findall(r"\w+", cleaned_sentence, flags=re.UNICODE)
            lemma_words = [word.lower() for word in words]

        if lemma_words:
            lemmatized_lines.append(" ".join(lemma_words))

    return lemmatized_lines


def lemmatize_node(state: LemmatizerState) -> LemmatizerState:
    """Process text through lemmatization pipeline."""
    input_text = state.get("text", "")
    if not input_text.strip():
        return {"lemmatized_lines": [], "error": "Empty input text."}

    lines = _lemmatize_text(input_text)
    return {"lemmatized_lines": lines, "error": ""}


def build_lemmatizer_graph() -> Any:
    graph_builder = StateGraph(cast(Any, LemmatizerState))
    graph_builder.add_node("lemmatize", cast(Any, lemmatize_node))
    graph_builder.add_edge(START, "lemmatize")
    graph_builder.add_edge("lemmatize", END)
    return graph_builder.compile()


def process(text: str) -> list[str]:
    graph = build_lemmatizer_graph()
    result: dict[str, Any] = graph.invoke({"text": text})
    return list(result.get("lemmatized_lines", []))


def main() -> None:
    if not INPUT.exists():
        print(f"Input file not found: {INPUT}")
        return

    source_text = INPUT.read_text(encoding="utf-8")
    graph = build_lemmatizer_graph()
    result: dict[str, Any] = graph.invoke({"text": source_text})

    error = str(result.get("error", "")).strip()
    if error:
        print(f"[WARN] {error}")

    output_lines = result.get("lemmatized_lines", [])
    OUTPUT.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"Lemmatizer processed: {INPUT} -> {OUTPUT}")


if __name__ == "__main__":
    main()

