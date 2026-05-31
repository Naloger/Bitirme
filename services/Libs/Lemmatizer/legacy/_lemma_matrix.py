from __future__ import annotations

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_english import (
    lemmatize as lemmatize_english,
)

MODEL_NAME = "en_core_web_sm"
corpus = ["The cats are chasing mice.", "A cat chasing a mouse is normal."]


# 2. Vectorization
# Note: passed token_pattern=None to avoid warnings when using a custom tokenizer
vectorizer = CountVectorizer(
    tokenizer=lemmatize_english, lowercase=False, token_pattern=None
)
term_doc_matrix = vectorizer.fit_transform(corpus)

# 3. Co-occurrence Matrix
co_occurrence = term_doc_matrix.T * term_doc_matrix
co_occurrence.setdiag(0)  # Zero out self-co-occurrence


# 4. Print Matrix Function
def print_co_occurrence_matrix(matrix, vectorizer):
    # Get the feature names (the lemmas) to use as labels
    words = vectorizer.get_feature_names_out()

    # Convert the sparse matrix to a dense pandas DataFrame
    df = pd.DataFrame(matrix.toarray(), columns=words, index=words)

    print("\n--- Word Co-occurrence Matrix ---")
    print(df)


def main() -> None:
    """Build and print the demo co-occurrence matrix."""
    print_co_occurrence_matrix(co_occurrence, vectorizer)


if __name__ == "__main__":
    main()
