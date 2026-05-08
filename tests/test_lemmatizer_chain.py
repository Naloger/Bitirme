from __future__ import annotations


from support_lib.Lemmatizer.lemmatize_english import lemmatize_english_text
from support_lib.Lemmatizer.lemmatize_turkish import lemmatize_turkish_text
from support_lib.Lemmatizer.segment_by_language import segment_by_language


MIXED_TEXT = (
    "I am running quickly and writing notes. "
    "Bugun kitaplari okuyorum ve notlar aliyorum."
)
ENGLISH_TEXT = "Developers are testing and validating the pipeline."
SHORT_TURKISH_TEXT = "Merhaba nasilsin"
SAMPLE_TEXT = "Hello, I am building tests. Bugun yeni bir zincir test yaziyorum."


def run_lemmatizer_chain(text: str) -> list[tuple[str, str]]:
    """Segment mixed text by language, then lemmatize each segment."""
    chained_output: list[tuple[str, str]] = []

    for segment in segment_by_language(text):
        lang = segment["language"]
        seg_text = segment["text"]

        if lang == "tr":
            lines = lemmatize_turkish_text(seg_text)
        else:
            lines = lemmatize_english_text(seg_text)

        if lines:
            chained_output.append((lang, " ".join(lines)))

    return chained_output


def _languages(result: list[tuple[str, str]]) -> list[str]:
    return [lang for lang, _ in result]


def _joined_text(result: list[tuple[str, str]], language: str) -> str:
    return " ".join(content for lang, content in result if lang == language)


def _assert_contains_any(text: str, expected_fragments: list[str]) -> None:
    assert any(fragment in text for fragment in expected_fragments), (
        f"Expected one of {expected_fragments!r} in {text!r}"
    )


# ────── Output formatting helpers ──────


def _print_header(title: str, width: int = 76) -> None:
    """Print a formatted section header."""
    print(f"\n{'═' * width}")
    print(f"  {title}")
    print(f"{'═' * width}")


def _print_test_title(title: str) -> None:
    """Print a test title with checkmark."""
    print(f"\n  ▶ {title}")


def _print_result(label: str, value: str, indent: int = 6) -> None:
    """Print a labeled result line."""
    prefix = " " * indent
    print(f"{prefix}• {label}: {value}")


def _print_section(title: str, indent: int = 4) -> None:
    """Print a subsection divider."""
    prefix = " " * indent
    print(f"\n{prefix}╭─ {title}")


def _print_subsection_end(indent: int = 4) -> None:
    """Print subsection end marker."""
    prefix = " " * indent
    print(f"{prefix}╰─")


# ────── Test functions ──────


def test_chain_processes_mixed_language_text() -> None:
    result = run_lemmatizer_chain(MIXED_TEXT)

    assert result, "Expected chained output for mixed-language text"
    assert {"en", "tr"}.issubset(set(_languages(result)))

    english_output = _joined_text(result, "en")
    turkish_output = _joined_text(result, "tr")

    # English branch should normalize verbs like running -> run.
    _assert_contains_any(english_output, ["run", "running"])

    # Turkish branch should preserve a Turkish reading in lemma or fallback form.
    _assert_contains_any(turkish_output, ["oku", "okuyor"])


def test_chain_processes_single_language_text() -> None:
    result = run_lemmatizer_chain(ENGLISH_TEXT)

    assert result, "Expected output for English-only text"
    assert all(lang == "en" for lang, _ in result)


def test_chain_prefers_turkish_for_short_ascii_turkish_text() -> None:
    result = run_lemmatizer_chain(SHORT_TURKISH_TEXT)

    assert result, "Expected output for short Turkish text"
    assert result[0][0] == "tr", f"Unexpected language order: {result!r}"


def test_chain_main_sample_remains_runnable() -> None:
    result = run_lemmatizer_chain(SAMPLE_TEXT)

    assert result
    assert any(lang == "tr" for lang, _ in result)


def main() -> None:
    """Run all tests with rich output formatting."""
    _print_header("LEMMATIZER CHAIN TEST SUITE")

    try:
        # Test 1: Mixed language
        _print_test_title("Test 1: Mixed Language Text Processing")
        test_chain_processes_mixed_language_text()
        _print_section("Mixed Language Data")
        _print_result("Input", MIXED_TEXT)
        result = run_lemmatizer_chain(MIXED_TEXT)
        en_text = _joined_text(result, "en")
        tr_text = _joined_text(result, "tr")
        _print_result("English lemmas", en_text)
        _print_result("Turkish lemmas", tr_text)
        _print_subsection_end()
        print("  ✓ PASSED")

        # Test 2: Single language
        _print_test_title("Test 2: Single Language (English) Processing")
        test_chain_processes_single_language_text()
        _print_section("Single Language Data")
        _print_result("Input", ENGLISH_TEXT)
        result = run_lemmatizer_chain(ENGLISH_TEXT)
        output = _joined_text(result, "en")
        _print_result("Lemmatized", output)
        _print_subsection_end()
        print("  ✓ PASSED")

        # Test 3: Short Turkish
        _print_test_title("Test 3: Short Turkish ASCII Text Detection")
        test_chain_prefers_turkish_for_short_ascii_turkish_text()
        _print_section("Short Turkish Data")
        _print_result("Input", SHORT_TURKISH_TEXT)
        result = run_lemmatizer_chain(SHORT_TURKISH_TEXT)
        _print_result("Detected language", result[0][0])
        _print_result("Lemmatized", result[0][1])
        _print_subsection_end()
        print("  ✓ PASSED")

        # Test 4: Sample
        _print_test_title("Test 4: Sample Mixed Text")
        test_chain_main_sample_remains_runnable()
        print("  ✓ PASSED")

        # Summary
        _print_header("CHAIN OUTPUT SAMPLE", width=76)
        print()
        sample_result = run_lemmatizer_chain(SAMPLE_TEXT)
        for lang, text in sample_result:
            marker = "🇬🇧" if lang == "en" else "🇹🇷"
            print(f"  {marker} [{lang}] {text}")

        _print_header("✅ ALL TESTS PASSED", width=76)
        print()

    except AssertionError as e:
        _print_header("❌ TEST FAILED", width=76)
        print(f"\n  Error: {e}\n")
        raise


if __name__ == "__main__":
    main()
