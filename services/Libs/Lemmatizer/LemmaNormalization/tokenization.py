from __future__ import annotations

from collections.abc import Iterable

import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import sent_tokenize, word_tokenize

from services.GraphBuilder.legacy.v1.config import TokenizerConfig
from services.Libs.Lemmatizer.LanguageSegmentation.segment_by_language import (
	segment_by_language,
)
from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_english import (
	lemmatize as lemmatize_english_text,
)
from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_turkish import (
	lemmatize as lemmatize_turkish_text,
)

_lemmatizer = WordNetLemmatizer()
_nltk_ready = False


def _ensure_nltk_data() -> None:
	global _nltk_ready
	if _nltk_ready:
		return
	for resource, path in [
		("punkt_tab", "tokenizers/punkt_tab"),
		("stopwords", "corpora/stopwords"),
		("wordnet", "corpora/wordnet"),
		("averaged_perceptron_tagger_eng", "taggers/averaged_perceptron_tagger_eng"),
	]:
		try:
			nltk.data.find(path)
		except LookupError:
			nltk.download(resource, quiet=True)
	_nltk_ready = True


def _penn_to_wordnet(tag: str) -> str:
	"""Map a Penn Treebank POS tag to a WordNet POS constant."""
	if tag.startswith("J"):
		return wordnet.ADJ
	if tag.startswith("V"):
		return wordnet.VERB
	if tag.startswith("R"):
		return wordnet.ADV
	return wordnet.NOUN


def _nltk_language_name(language_code: str) -> str:
	"""Map a short language code to the NLTK language name used by tokenizers."""
	return {"en": "english", "tr": "turkish"}.get(language_code, language_code)


def _build_stop_set(config: TokenizerConfig, language_code: str) -> set[str]:
	"""Build a normalized stopword set for one segment language."""
	stop_set: set[str] = set()
	if config.use_stopwords:
		try:
			stop_set = set(stopwords.words(_nltk_language_name(language_code)))
		except LookupError:
			stop_set = set()
	stop_set |= {w.lower() for w in config.extra_stopwords}
	return stop_set


def _normalize_tokens(
	tokens: Iterable[str],
	*,
	config: TokenizerConfig,
	stop_set: set[str],
) -> list[str]:
	"""Apply common token filters after language-specific lemmatization."""
	normalized: list[str] = []
	for token in tokens:
		cleaned = token.lower() if config.lowercase else token
		cleaned = cleaned.strip()
		if not cleaned:
			continue
		if not cleaned.isalpha():
			continue
		if len(cleaned) < config.min_token_length:
			continue
		if cleaned in stop_set:
			continue
		normalized.append(cleaned)
	return normalized


def _tokenize_english_segment(text: str, config: TokenizerConfig) -> list[list[str]]:
	"""Tokenize and lemmatize one English segment."""
	_ensure_nltk_data()
	stop_set = _build_stop_set(config, "en")
	result: list[list[str]] = []

	if config.pos_filter is None:
		for line in lemmatize_english_text(text):
			tokens = _normalize_tokens(line.split(), config=config, stop_set=stop_set)
			if tokens:
				result.append(tokens)
		return result

	for sentence in sent_tokenize(text, language="english"):
		raw_tokens = word_tokenize(sentence, language="english")
		tagged: list[tuple[str, str]] = nltk.pos_tag(raw_tokens)

		tokens: list[str] = []
		for word, tag in tagged:
			if config.lowercase:
				word = word.lower()

			if not word.isalpha():
				continue
			if len(word) < config.min_token_length:
				continue
			if word in stop_set:
				continue
			if config.pos_filter is not None and not any(
				tag.startswith(prefix) for prefix in config.pos_filter
			):
				continue

			lemma = _lemmatizer.lemmatize(word, _penn_to_wordnet(tag))
			tokens.append(lemma)

		if tokens:
			result.append(tokens)

	return result


def _tokenize_turkish_segment(text: str, config: TokenizerConfig) -> list[list[str]]:
	"""Tokenize and lemmatize one Turkish segment."""
	stop_set = _build_stop_set(config, "tr")
	result: list[list[str]] = []

	for line in lemmatize_turkish_text(text):
		tokens = _normalize_tokens(line.split(), config=config, stop_set=stop_set)
		if tokens:
			result.append(tokens)

	return result


def _tokenize_and_lemmatize(text: str, config: TokenizerConfig) -> list[list[str]]:
	"""Return one token list per language-aware segment after lemmatization."""
	result: list[list[str]] = []
	for segment in segment_by_language(text):
		segment_text = segment["text"]
		language = segment["language"]
		if language == "tr":
			result.extend(_tokenize_turkish_segment(segment_text, config))
		else:
			result.extend(_tokenize_english_segment(segment_text, config))
	return result


def lemmatize_text(text: str) -> list[str]:
	"""Return language-aware lemmatized lines for mixed English/Turkish text."""
	lines: list[str] = []
	for segment in segment_by_language(text):
		segment_text = segment["text"]
		if segment["language"] == "tr":
			lines.extend(lemmatize_turkish_text(segment_text))
		else:
			lines.extend(lemmatize_english_text(segment_text))
	return lines

