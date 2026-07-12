"""Lemma matrix Endpoints: store graph-edge triples with owner IDs."""

import json
import re
from typing import Any, List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, model_validator
from sqlalchemy import func
from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from backend.api.DataSchemas.api_data_schemas_lemma_matrix import (
	LemmaConnectionCreate,
	LemmaConnectionRead,
	LemmaConnectionUpdate,
)
from backend.api.api_init import get_lemma_matrix_session
from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
	LemmaMatrixModel,
	VocabularyModel,
)
from Libs.Lemmatizer.lemma_matrix import LemmaMatrixBuilder

router = APIRouter()


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


def _clean_text_to_json_safe(text: str) -> str:
	"""Clean input text to be JSON-acceptable by escaping/removing double quotes,
	strip backslashes, and replace newlines/tabs with space.
	"""
	cleaned = text.replace('"', '').replace('\\', '').replace('\n', ' ').replace('\r', ' ')
	return re.sub(r'\s+', ' ', cleaned).strip()


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


def _get_or_create_vocab_id(session: Session, word: str) -> int:
	"""Get vocabulary ID for a normalized word, creating it if it does not exist."""
	normalized = _normalize_word(word)
	if not normalized:
		raise ValueError("Normalized word cannot be empty")
	
	existing = session.exec(select(VocabularyModel).where(cast(Any, VocabularyModel.word == normalized))).first()
	if existing is not None:
		existing_vocab = cast(VocabularyModel, existing)
		vocab_id = existing_vocab.id
		if vocab_id is not None:
			return vocab_id
		raise ValueError("Database integrity error: Vocabulary ID is None")
	
	new_vocab = VocabularyModel(word=normalized)
	session.add(new_vocab)
	session.flush()
	
	vocab_id = new_vocab.id
	if vocab_id is not None:
		return vocab_id
	raise ValueError("Failed to retrieve ID for newly created vocabulary")


def _next_matrix_id(session: Session) -> int:
	max_id = session.exec(select(func.max(LemmaMatrixModel.id))).one()
	return int(max_id or 0) + 1


def _upsert_pairs(session: Session, pairs: list[dict], overwrite: bool = False) -> tuple[int, int]:
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
		w1 = item.get("word1")
		w2 = item.get("word2")
		word1 = _normalize_word(str(w1) if w1 is not None else "")
		word2 = _normalize_word(str(w2) if w2 is not None else "")

		# Skip if either word is empty after normalization
		if not word1 or not word2:
			continue

		# Validate and ensure weight is a non-negative int
		weight = _validate_weight(item.get("weight"))

		# Resolve vocabulary IDs
		vocab1_id = _get_or_create_vocab_id(session, word1)
		vocab2_id = _get_or_create_vocab_id(session, word2)

		existing = session.exec(
			select(LemmaMatrixModel).where(
				cast(Any, LemmaMatrixModel.vocab1_id == vocab1_id),
				cast(Any, LemmaMatrixModel.vocab2_id == vocab2_id),
			)
		).first()

		if existing is not None:
			existing_matrix = cast(LemmaMatrixModel, existing)
			if overwrite:
				existing_matrix.weight = weight
			else:
				existing_matrix.weight = int(existing_matrix.weight or 0) + weight
			session.add(existing_matrix)
			updated += 1
		else:
			new_rec = LemmaMatrixModel(
				id=current_id,
				vocab1_id=vocab1_id,
				vocab2_id=vocab2_id,
				weight=weight,
			)
			session.add(new_rec)
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
	v1 = aliased(VocabularyModel)
	v2 = aliased(VocabularyModel)
	
	statement = (
		select(
			LemmaMatrixModel.id,
			cast(Any, v1.word).label("word1"),
			cast(Any, v2.word).label("word2"),
			LemmaMatrixModel.weight
		)
		.join(cast(Any, v1), onclause=cast(Any, LemmaMatrixModel.vocab1_id == v1.id))
		.join(cast(Any, v2), onclause=cast(Any, LemmaMatrixModel.vocab2_id == v2.id))
		.offset(skip)
		.limit(limit)
	)
	results = session.exec(statement).all()
	connections = []
	for r in results:
		if r is not None:
			r_tuple = cast(tuple, r)
			connections.append({
				"id": int(r_tuple[0]) if r_tuple[0] is not None else 0,
				"word1": str(r_tuple[1]),
				"word2": str(r_tuple[2]),
				"weight": int(r_tuple[3])
			})
	return connections


@router.get(
	"/connections/{conn_id}",
	response_model=LemmaConnectionRead,
	tags=["LemmaConnections"],
)
def get_connection(conn_id: int, session: Session = Depends(get_lemma_matrix_session)):
	v1 = aliased(VocabularyModel)
	v2 = aliased(VocabularyModel)
	
	statement = (
		select(
			LemmaMatrixModel.id,
			cast(Any, v1.word).label("word1"),
			cast(Any, v2.word).label("word2"),
			LemmaMatrixModel.weight
		)
		.join(cast(Any, v1), onclause=cast(Any, LemmaMatrixModel.vocab1_id == v1.id))
		.join(cast(Any, v2), onclause=cast(Any, LemmaMatrixModel.vocab2_id == v2.id))
		.where(cast(Any, LemmaMatrixModel.id == conn_id))
	)
	r = session.exec(statement).first()
	if r is None:
		raise HTTPException(status_code=404, detail="Connection not found")
	r_tuple = cast(tuple, r)
	return {
		"id": int(r_tuple[0]) if r_tuple[0] is not None else 0,
		"word1": str(r_tuple[1]),
		"word2": str(r_tuple[2]),
		"weight": int(r_tuple[3])
	}


@router.put(
	"/connections/{conn_id}",
	response_model=LemmaConnectionRead,
	tags=["LemmaConnections"],
)
def update_connection(conn_id: int, payload: LemmaConnectionUpdate, session: Session = Depends(get_lemma_matrix_session)):
	conn = session.exec(select(LemmaMatrixModel).where(cast(Any, LemmaMatrixModel.id == conn_id))).first()
	if conn is None:
		raise HTTPException(status_code=404, detail="Connection not found")
	
	conn_model = cast(LemmaMatrixModel, conn)
	update_data = payload.model_dump(exclude_unset=True)
	
	if "word1" in update_data and update_data["word1"]:
		conn_model.vocab1_id = _get_or_create_vocab_id(session, str(update_data["word1"]))
	if "word2" in update_data and update_data["word2"]:
		conn_model.vocab2_id = _get_or_create_vocab_id(session, str(update_data["word2"]))
	if "weight" in update_data and update_data["weight"] is not None:
		conn_model.weight = _validate_weight(update_data["weight"])

	session.add(conn_model)
	session.commit()
	
	v1 = aliased(VocabularyModel)
	v2 = aliased(VocabularyModel)
	statement = (
		select(
			LemmaMatrixModel.id,
			cast(Any, v1.word).label("word1"),
			cast(Any, v2.word).label("word2"),
			LemmaMatrixModel.weight
		)
		.join(cast(Any, v1), onclause=cast(Any, LemmaMatrixModel.vocab1_id == v1.id))
		.join(cast(Any, v2), onclause=cast(Any, LemmaMatrixModel.vocab2_id == v2.id))
		.where(cast(Any, LemmaMatrixModel.id == conn_id))
	)
	r = session.exec(statement).first()
	if r is None:
		raise HTTPException(status_code=404, detail="Connection not found")
	r_tuple = cast(tuple, r)
	return {
		"id": int(r_tuple[0]) if r_tuple[0] is not None else 0,
		"word1": str(r_tuple[1]),
		"word2": str(r_tuple[2]),
		"weight": int(r_tuple[3])
	}


@router.delete(
	"/connections",
	response_model=dict,
	tags=["LemmaConnections"],
)
def clear_all_connections(session: Session = Depends(get_lemma_matrix_session)):
	"""Delete all connections from the lemma matrix database."""
	from sqlmodel import delete
	try:
		session.exec(delete(LemmaMatrixModel))
		session.commit()
		return {"message": "Successfully cleared all connections from the database."}
	except Exception as e:
		session.rollback()
		raise HTTPException(status_code=500, detail=f"Failed to clear database: {e}")


# Payload model for building matrix from text(s)
class TextsPayload(BaseModel):
	text: Optional[str] = None
	texts: Optional[list[str]] = None
	min_weight: int = 0
	window_size: Optional[int] = None
	overwrite: bool = False

	@model_validator(mode="after")
	def at_least_one(self):
		# Instance-level validator: ensure at least one of text/texts provided
		if not self.text and not self.texts:
			raise ValueError("Either 'text' or 'texts' must be provided")
		return self


async def _parse_and_build(request: Request, session: Session, save_to_db: bool = True) -> dict:
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
		match1 = re.match(r'^\s*{\s*"text"\s*:\s*"(.*)"\s*}\s*$', body_str, re.DOTALL)
		if match1:
			payload_dict["text"] = match1.group(1)
		else:
			# 2. Match {"text": "<content>", "min_weight": <digits>}
			match2 = re.match(r'^\s*{\s*"text"\s*:\s*"(.*)"\s*,\s*"min_weight"\s*:\s*(\d+)\s*}\s*$', body_str, re.DOTALL)
			if match2:
				payload_dict["text"] = match2.group(1)
				payload_dict["min_weight"] = int(match2.group(2))
			else:
				# 3. Match {"min_weight": <digits>, "text": "<content>"}
				match3 = re.match(r'^\s*{\s*"min_weight"\s*:\s*(\d+)\s*,\s*"text"\s*:\s*"(.*)"\s*}\s*$', body_str, re.DOTALL)
				if match3:
					payload_dict["text"] = match3.group(2)
					payload_dict["min_weight"] = int(match3.group(1))
				else:
					# If all matches fail, raise the original JSON decode error as a 400 Bad Request
					raise HTTPException(status_code=400, detail=f"Invalid JSON format: {exc}")

	text = payload_dict.get("text")
	texts = payload_dict.get("texts")
	min_weight = payload_dict.get("min_weight", 0)
	window_size = payload_dict.get("window_size", None)
	overwrite = payload_dict.get("overwrite", False)

	if not isinstance(overwrite, bool):
		overwrite = str(overwrite).lower() in ("true", "1", "yes")

	if "window_size" not in payload_dict:
		window_match = re.search(r'"window_size"\s*:\s*(\d+)', body_str)
		if window_match:
			window_size = int(window_match.group(1))

	if "overwrite" not in payload_dict:
		overwrite_match = re.search(r'"overwrite"\s*:\s*(true|false)', body_str, re.IGNORECASE)
		if overwrite_match:
			overwrite = overwrite_match.group(1).lower() == "true"

	if not text and not texts:
		raise HTTPException(status_code=400, detail="Either 'text' or 'texts' must be provided")

	texts_list: list[str] = []
	if text and isinstance(text, str):
		texts_list.append(_clean_text_to_json_safe(text))
	if texts:
		if isinstance(texts, list):
			texts_list.extend([_clean_text_to_json_safe(str(t)) for t in texts if t is not None])
		elif isinstance(texts, str):
			texts_list.append(_clean_text_to_json_safe(texts))

	builder = LemmaMatrixBuilder()
	vectorizer, matrix = builder.build_cooccurrence_matrix(texts_list, window_size=window_size)
	pairs = builder.extract_matrix_pairs(matrix, vectorizer)

	# Optionally filter by min_weight
	if min_weight and min_weight >= 0:
		pairs = [p for p in pairs if p["weight"] >= min_weight]

	if not pairs:
		return {"message": "No co-occurrence pairs found for the provided text(s).", "pairs": []}

	if save_to_db:
		# Upsert using helper (with overwrite option)
		created, updated = _upsert_pairs(session, pairs, overwrite=overwrite)
		return {"message": f"Successfully built matrix: {len(pairs)} processed ({created} created, {updated} updated)."}
	else:
		return {
			"message": f"Successfully built matrix (dry run): {len(pairs)} pairs generated.",
			"pairs": pairs
		}


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
							"min_weight": {"type": "integer", "default": 0},
							"window_size": {"type": "integer", "default": 1},
							"overwrite": {"type": "boolean", "default": False}
						}
					}
				}
			}
		}
	}
)
async def build_matrix_from_text(request: Request, session: Session = Depends(get_lemma_matrix_session)):
	"""Accepts a single text or a list of texts, builds a lemmatized co-occurrence matrix,
	extracts word pairs without storing them into the database.
	"""
	return await _parse_and_build(request, session, save_to_db=False)


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
							"min_weight": {"type": "integer", "default": 0},
							"window_size": {"type": "integer", "default": 1},
							"overwrite": {"type": "boolean", "default": False}
						}
					}
				}
			}
		}
	}
)
async def build_and_upsert(request: Request, session: Session = Depends(get_lemma_matrix_session)):
	"""Alias endpoint: build co-occurrence pairs from text(s) and upsert into the DB."""
	return await _parse_and_build(request, session, save_to_db=True)


@router.post(
	"/to_lemma_list",
	response_model=List[str],
	tags=["LemmaConnections"],
	openapi_extra={
		"requestBody": {
			"content": {
				"application/json": {
					"schema": {
						"type": "object",
						"properties": {
							"text": {
								"type": "string",
								"example": "The \"apple\", \"banana\", and \"cherry\" are fruits."
							}
						},
						"required": ["text"]
					}
				},
				"text/plain": {
					"schema": {
						"type": "string",
						"example": "Hello, \"world\", let's test!"
					}
				}
			}
		}
	}
)
async def to_lemma_list(request: Request):
	"""Accepts a text input, cleans it to a JSON-acceptable/safe level by escaping or removing double quotes/commas,
	and returns a list of lemmatized words.
	"""
	body_bytes = await request.body()
	body_str = body_bytes.decode("utf-8").strip()

	text = ""
	if body_str:
		# Check if it starts with { (indicating JSON)
		if body_str.startswith("{") or body_str.startswith("["):
			try:
				data = json.loads(body_str)
				if isinstance(data, dict):
					text = data.get("text", "")
				elif isinstance(data, str):
					text = data
			except json.JSONDecodeError:
				# Clean quotes inside malformed JSON object
				match = re.match(r'^\s*{\s*"text"\s*:\s*"(.*)"\s*}\s*$', body_str, re.DOTALL)
				if match:
					text = match.group(1)
				else:
					text = body_str
		else:
			# Raw string
			text = body_str

	# Clean the input text to JSON safe level
	cleaned_text = _clean_text_to_json_safe(text)

	builder = LemmaMatrixBuilder()
	return builder.tokenize(cleaned_text)
