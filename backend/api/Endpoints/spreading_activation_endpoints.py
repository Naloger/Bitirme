"""Spreading Activation endpoint — query related words via Leiden-aware activation spreading."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from backend.api.api_init import get_lemma_matrix_session
from Libs.Leiden.leiden_spreading_activation import spreading_activation

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────

class SpreadingActivationRequest(BaseModel):
    """Parameters for a spreading activation query."""

    seed_words: List[str] = Field(
        ...,
        min_length=1,
        description="One or more words to activate as seeds.",
        examples=[["sun", "roman", "god"]],
    )
    decay: float = Field(
        0.8,
        gt=0.0,
        le=1.0,
        description="Decay factor per hop (0 < decay ≤ 1).",
    )
    firing_threshold: float = Field(
        0.01,
        ge=0.0,
        description="Minimum activation for a node to keep propagating.",
    )
    max_steps: int = Field(
        5,
        ge=1,
        le=50,
        description="Maximum number of propagation iterations.",
    )
    intra_community_boost: float = Field(
        1.0,
        ge=0.0,
        description="Multiplier for edges within the same Leiden community.",
    )
    inter_community_penalty: float = Field(
        0.3,
        ge=0.0,
        description="Multiplier for edges crossing community boundaries.",
    )
    initial_activation: float = Field(
        1.0,
        gt=0.0,
        description="Starting activation value assigned to each seed.",
    )
    top_k: Optional[int] = Field(
        None,
        ge=1,
        description="If set, return only the top-K activated words.",
    )


class ActivatedWord(BaseModel):
    """A single word and its final activation score."""

    word: str
    score: float


class SpreadingActivationResponse(BaseModel):
    """Full response from the spreading activation endpoint."""

    seed_words: List[str]
    activated_count: int
    results: List[ActivatedWord]
    seed_results: List[ActivatedWord] = Field(
        default=[],
        description="The activated seed words themselves.",
    )
    spreaded_results: List[ActivatedWord] = Field(
        default=[],
        description="The activated words discovered via spreading (excluding seeds).",
    )


# ── Endpoint ──────────────────────────────────────────────────────────────

@router.post(
    "/spreading_activation",
    response_model=SpreadingActivationResponse,
    tags=["SpreadingActivation"],
    summary="Leiden-aware Spreading Activation",
    description=(
        "Activate seed words and propagate activation through the PPMI word graph. "
        "Activation spreads faster within Leiden communities and attenuates across "
        "community boundaries."
    ),
)
def run_spreading_activation(
    payload: SpreadingActivationRequest,
    session: Session = Depends(get_lemma_matrix_session),
) -> SpreadingActivationResponse:
    """Run spreading activation and return ranked word activations."""
    try:
        scores = spreading_activation(
            session=session,
            seed_words=payload.seed_words,
            decay=payload.decay,
            firing_threshold=payload.firing_threshold,
            max_steps=payload.max_steps,
            intra_community_boost=payload.intra_community_boost,
            inter_community_penalty=payload.inter_community_penalty,
            initial_activation=payload.initial_activation,
            top_k=payload.top_k,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Spreading activation failed: {exc}",
        )

    results = [ActivatedWord(word=w, score=s) for w, s in scores.items()]

    # Separate seeds from spreaded results using Lemmatizer pipeline
    from Libs.Lemmatizer.lemma_matrix import LemmaMatrixBuilder
    builder = LemmaMatrixBuilder()

    normalized_seeds = set()
    for w in payload.seed_words:
        normalized_seeds.update(builder.tokenize(w))

    seed_results = []
    spreaded_results = []

    for item in results:
        if item.word in normalized_seeds:
            seed_results.append(item)
        else:
            spreaded_results.append(item)

    return SpreadingActivationResponse(
        seed_words=payload.seed_words,
        activated_count=len(results),
        results=results,
        seed_results=seed_results,
        spreaded_results=spreaded_results,
    )
