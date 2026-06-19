"""Lemma matrix Endpoints: store graph-edge triples with owner IDs."""

from typing import List
import re
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlmodel import Session, select

from backend.api.DataSchemas.api_data_schemas_lemma_matrix import (
	LemmaConnectionCreate,
	LemmaConnectionRead,
	LemmaConnectionUpdate,
)
from backend.api.api_init import get_lemma_matrix_session
from backend.database.ORMSchemas.orm_schema_lemma_matrix import LemmaMatrixModel


router = APIRouter()
from pydantic import BaseModel, model_validator
from typing import Optional

# Lemmatizer
from Libs.Lemmatizer.lemma_matrix import LemmaMatrixBuilder


def _normalize_word(word: str) -> str:
	"""Normalize a word: remove special chars/numbers/punctuation, lowercase, and strip whitespace.
	Keeps only alphabetic characters and spaces.
	"""
	if not isinstance(word, str):
		word = str(word)
	# Remove all non-alphabetic characters except spaces
	cleaned = re.sub(r'[^a-zA-Z\s]', '', word)
	# Normalize whitespace: collapse multiple spaces to single space and strip
	normalized = ' '.join(cleaned.split())
	return normalized.lower().strip()


def _validate_weight(weight: int | None) -> int:
	"""Validate and convert weight to a positive integer. Default to 0 if invalid."""
	if weight is None:
		return 0
	try:
		w = int(weight)
		# Allow non-negative weights only; negative weights are invalid
		return max(0, w)
	except (TypeError, ValueError):
		return 0


def _next_matrix_id(session: Session) -> int:
	max_id = session.exec(select(func.max(LemmaMatrixModel.id))).one()
	return int(max_id or 0) + 1


def _upsert_pairs(session: Session, pairs: list[dict]) -> tuple[int, int]:
	"""Upsert a list of {'word1','word2','weight'} dicts into the DB.
	Normalizes words (lowercase + trim) and validates weights (non-negative int).
	Returns (created_count, updated_count).
	"""
	next_id = _next_matrix_id(session)
	current_id = next_id
	created = 0
	updated = 0

	for item in pairs:
		# Normalize words: lowercase and strip whitespace
		word1 = _normalize_word(item.get("word1", ""))
		word2 = _normalize_word(item.get("word2", ""))

		# Skip if either word is empty after normalization
		if not word1 or not word2:
			continue

		# Validate and ensure weight is a non-negative int
		weight = _validate_weight(item.get("weight"))

		existing = session.exec(
			select(LemmaMatrixModel).where(
				LemmaMatrixModel.word1 == word1,
				LemmaMatrixModel.word2 == word2,
			)
		).first()

		if existing:
			existing.weight = int(existing.weight or 0) + weight
			session.add(existing)
			updated += 1
		else:
			new_rec = LemmaMatrixModel(
				id=current_id,
				word1=word1,
				word2=word2,
				weight=weight,
			)
			session.add(new_rec)
			# Flush to make the new record visible to subsequent queries in this batch
			session.flush()
			current_id += 1
			created += 1

	session.commit()
	return created, updated


@router.post(
	"/connections",
	response_model=dict,
	tags=["LemmaConnections"],
)
def save_connections(payload: List[LemmaConnectionCreate], session: Session = Depends(get_lemma_matrix_session)):
	"""Receives a list of ( word1, word2, weight) rows and bulk-inserts them into the lemma matrix DB."""
	# Use helper to upsert pairs built from payload
	pairs = [{"word1": item.word1, "word2": item.word2, "weight": item.weight} for item in payload]
	created, updated = _upsert_pairs(session, pairs)

	return {"message": f"Successfully upserted {len(pairs)} connections ({created} created, {updated} updated)."}


@router.get(
	"/connections",
	response_model=list[LemmaConnectionRead],
	tags=["LemmaConnections"],
)
def get_all_connections(
	skip: int = Query(0, ge=0),
	limit: int = Query(100, ge=1, le=500),
	session: Session = Depends(get_lemma_matrix_session),
):
	statement = select(LemmaMatrixModel).offset(skip).limit(limit)
	return session.exec(statement).all()


@router.get(
	"/connections/{conn_id}",
	response_model=LemmaConnectionRead,
	tags=["LemmaConnections"],
)
def get_connection(conn_id: int, session: Session = Depends(get_lemma_matrix_session)):
	conn = session.exec(select(LemmaMatrixModel).where(LemmaMatrixModel.id == conn_id)).first()
	if not conn:
		raise HTTPException(status_code=404, detail="Connection not found")
	return conn


@router.put(
	"/connections/{conn_id}",
	response_model=LemmaConnectionRead,
	tags=["LemmaConnections"],
)
def update_connection(conn_id: int, payload: LemmaConnectionUpdate, session: Session = Depends(get_lemma_matrix_session)):
	conn = session.exec(select(LemmaMatrixModel).where(LemmaMatrixModel.id == conn_id)).first()
	if not conn:
		raise HTTPException(status_code=404, detail="Connection not found")

	update_data = payload.model_dump(exclude_unset=True)
	for key, value in update_data.items():
		setattr(conn, key, value)

	session.add(conn)
	session.commit()
	session.refresh(conn)

	return conn


# Payload model for building matrix from text(s)
class TextsPayload(BaseModel):
	text: Optional[str] = None
	texts: Optional[list[str]] = None
	min_weight: int = 1

	@model_validator(mode="after")
	def at_least_one(self):
		# Instance-level validator: ensure at least one of text/texts provided
		if not self.text and not self.texts:
			raise ValueError("Either 'text' or 'texts' must be provided")
		return self


async def _parse_and_build(request: Request, session: Session) -> dict:
	body_bytes = await request.body()
	body_str = body_bytes.decode("utf-8")

	# Try standard JSON parsing first
	try:
		payload_dict = json.loads(body_str)
	except json.JSONDecodeError as exc:
		# Lenient fallback parsing:
		# If the JSON is malformed due to unescaped double quotes in "text",
		# we can extract the content of "text" and optional "min_weight" using regex.
		payload_dict = {}
		
		# 1. Match {"text": "<content>"}
		match1 = re.match(r'^\s*\{\s*"text"\s*:\s*"(.*)"\s*\}\s*$', body_str, re.DOTALL)
		if match1:
			payload_dict["text"] = match1.group(1)
		else:
			# 2. Match {"text": "<content>", "min_weight": <digits>}
			match2 = re.match(r'^\s*\{\s*"text"\s*:\s*"(.*)"\s*,\s*"min_weight"\s*:\s*(\d+)\s*\}\s*$', body_str, re.DOTALL)
			if match2:
				payload_dict["text"] = match2.group(1)
				payload_dict["min_weight"] = int(match2.group(2))
			else:
				# 3. Match {"min_weight": <digits>, "text": "<content>"}
				match3 = re.match(r'^\s*\{\s*"min_weight"\s*:\s*(\d+)\s*,\s*"text"\s*:\s*"(.*)"\s*\}\s*$', body_str, re.DOTALL)
				if match3:
					payload_dict["text"] = match3.group(2)
					payload_dict["min_weight"] = int(match3.group(1))
				else:
					# If all matches fail, raise the original JSON decode error as a 400 Bad Request
					raise HTTPException(status_code=400, detail=f"Invalid JSON format: {exc}")

	text = payload_dict.get("text")
	texts = payload_dict.get("texts")
	min_weight = payload_dict.get("min_weight", 1)

	if not text and not texts:
		raise HTTPException(status_code=400, detail="Either 'text' or 'texts' must be provided")

	texts_list: list[str] = []
	if text:
		texts_list.append(text)
	if texts:
		if isinstance(texts, list):
			texts_list.extend(texts)
		elif isinstance(texts, str):
			texts_list.append(texts)

	builder = LemmaMatrixBuilder()
	vectorizer, matrix = builder.build_cooccurrence_matrix(texts_list)
	pairs = builder.extract_matrix_pairs(matrix, vectorizer)

	# Optionally filter by min_weight
	if min_weight and min_weight > 1:
		pairs = [p for p in pairs if p["weight"] >= min_weight]

	if not pairs:
		return {"message": "No co-occurrence pairs found for the provided text(s)."}

	# Upsert using helper
	created, updated = _upsert_pairs(session, pairs)

	return {"message": f"Successfully built matrix: {len(pairs)} processed ({created} created, {updated} updated)."}


@router.post(
	"/build",
	response_model=dict,
	tags=["LemmaConnections"],
	openapi_extra={
		"requestBody": {
			"content": {
				"application/json": {
					"schema": {
						"type": "object",
						"properties": {
							"text": {"type": "string", "example": "Sol is the personification of the Sun and a god in ancient Roman religion."},
							"texts": {"type": "array", "items": {"type": "string"}},
							"min_weight": {"type": "integer", "default": 1}
						}
					}
				}
			}
		}
	}
)
async def build_matrix_from_text(request: Request, session: Session = Depends(get_lemma_matrix_session)):
	"""Accepts a single text or a list of texts, builds a lemmatized co-occurrence matrix,
	extracts word pairs and stores them into the lemma matrix database.
	"""
	return await _parse_and_build(request, session)


@router.post(
	"/build_and_upsert",
	response_model=dict,
	tags=["LemmaConnections"],
	openapi_extra={
		"requestBody": {
			"content": {
				"application/json": {
					"schema": {
						"type": "object",
						"properties": {
							"text": {"type": "string", "example": "Sol is the personification of the Sun and a god in ancient Roman religion."},
							"texts": {"type": "array", "items": {"type": "string"}},
							"min_weight": {"type": "integer", "default": 1}
						}
					}
				}
			}
		}
	}
)
async def build_and_upsert(request: Request, session: Session = Depends(get_lemma_matrix_session)):
	"""Alias endpoint: build co-occurrence pairs from text(s) and upsert into the DB."""
	return await _parse_and_build(request, session)

