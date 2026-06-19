import sys
from pathlib import Path
import uuid
import re
from fastapi.testclient import TestClient

# Ensure project root is on sys.path so `backend` imports work during pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.api.api_init import app


def test_normalization_case_insensitive():
	"""Test that word normalization (lowercasing) works correctly."""
	client = TestClient(app)

	unique = str(uuid.uuid4())[:8]

	# Create two payloads with different cases but same normalized form
	# When sanitized, dashes and numbers are removed from UUID
	payload1 = [
		{"word1": f"APPLE-{unique}", "word2": f"BANANA-{unique}", "weight": 5}
	]
	payload2 = [
		{"word1": f"apple{unique}", "word2": f"banana{unique}", "weight": 3}
	]

	# First POST
	resp1 = client.post("/api/lemma_matrix/connections", json=payload1)
	assert resp1.status_code == 200
	body1 = resp1.json()
	assert "created" in body1.get("message", ""), body1

	# Fetch and verify it was stored in normalized form
	list_resp1 = client.get("/api/lemma_matrix/connections?skip=0&limit=500")
	assert list_resp1.status_code == 200
	data1 = list_resp1.json()
	
	# Extract just the alphabetic part from unique (numbers removed)
	alpha_unique = ''.join(c for c in unique if c.isalpha())
	
	pair1 = [d for d in data1 if d.get("word1") == f"apple{alpha_unique}" and d.get("word2") == f"banana{alpha_unique}"]
	assert len(pair1) >= 1, "Expected to find normalized pair (lowercased, special chars removed)"
	weight1 = pair1[0]["weight"]
	assert weight1 == 5

	# Second POST: same words format, should increment existing
	resp2 = client.post("/api/lemma_matrix/connections", json=payload2)
	assert resp2.status_code == 200
	body2 = resp2.json()
	assert "updated" in body2.get("message", ""), body2

	# Fetch again and verify weight was incremented
	list_resp2 = client.get("/api/lemma_matrix/connections?skip=0&limit=500")
	assert list_resp2.status_code == 200
	data2 = list_resp2.json()
	
	pair2 = [d for d in data2 if d.get("word1") == f"apple{alpha_unique}" and d.get("word2") == f"banana{alpha_unique}"]
	assert len(pair2) >= 1
	weight2 = pair2[0]["weight"]
	assert weight2 == weight1 + 3, f"Expected weight {weight1 + 3}, got {weight2}"


def test_normalization_whitespace_trimming():
	"""Test that leading/trailing whitespace is trimmed."""
	client = TestClient(app)

	unique = str(uuid.uuid4())[:8]
	alpha_unique = ''.join(c for c in unique if c.isalpha())

	# Payload with leading/trailing whitespace
	payload = [
		{"word1": f"  APPLE-{unique}  ", "word2": f"  BANANA-{unique}  ", "weight": 2}
	]

	resp = client.post("/api/lemma_matrix/connections", json=payload)
	assert resp.status_code == 200

	# Fetch and verify stored in trimmed, lowercased, sanitized form
	list_resp = client.get("/api/lemma_matrix/connections?skip=0&limit=500")
	assert list_resp.status_code == 200
	data = list_resp.json()

	# Should be stored as lowercased, trimmed, and with dashes/numbers removed
	pair = [d for d in data if d.get("word1") == f"apple{alpha_unique}" and d.get("word2") == f"banana{alpha_unique}"]
	assert len(pair) >= 1, "Expected to find trimmed, normalized pair"
	assert pair[0]["weight"] == 2


def test_negative_weight_validation():
	"""Test that negative weights are rejected."""
	client = TestClient(app)

	unique = str(uuid.uuid4())[:8]

	# Try to POST with negative weight - should be rejected by Pydantic validator
	payload = [
		{"word1": f"apple-{unique}", "word2": f"banana-{unique}", "weight": -5}
	]

	resp = client.post("/api/lemma_matrix/connections", json=payload)
	# Should get 422 Validation Error from Pydantic
	assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.json()}"


def test_empty_word_validation():
	"""Test that empty or whitespace-only words are rejected."""
	client = TestClient(app)

	unique = str(uuid.uuid4())[:8]

	# Try to POST with empty word1
	payload1 = [
		{"word1": "", "word2": f"banana-{unique}", "weight": 1}
	]

	resp1 = client.post("/api/lemma_matrix/connections", json=payload1)
	assert resp1.status_code == 422, f"Expected 422 for empty word1, got {resp1.status_code}"

	# Try to POST with whitespace-only word2
	payload2 = [
		{"word1": f"apple-{unique}", "word2": "   ", "weight": 1}
	]

	resp2 = client.post("/api/lemma_matrix/connections", json=payload2)
	assert resp2.status_code == 422, f"Expected 422 for whitespace-only word2, got {resp2.status_code}"


def test_character_sanitization_removes_numbers_punctuation():
	"""Test that numbers, punctuation, and special characters are removed from words."""
	client = TestClient(app)

	unique = str(uuid.uuid4())[:8]
	alpha_unique = ''.join(c for c in unique if c.isalpha())

	# Payload with numbers, punctuation, and special characters
	payload = [
		{"word1": f"apple-2-{unique}", "word2": f"fruit.123{unique}", "weight": 1},
		{"word1": f"APPLE_{unique}", "word2": f"FRUIT,{unique}", "weight": 2},
	]

	resp = client.post("/api/lemma_matrix/connections", json=payload)
	assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

	# Fetch and verify stored in sanitized form (numbers and punctuation removed)
	list_resp = client.get("/api/lemma_matrix/connections?skip=0&limit=500")
	assert list_resp.status_code == 200
	data = list_resp.json()
	
	# Both should normalize to: apple{alpha_unique} and fruit{alpha_unique}
	# After removing dashes, underscores, dots, commas, and all numbers
	pair = [d for d in data if d.get("word1") == f"apple{alpha_unique}" and d.get("word2") == f"fruit{alpha_unique}"]
	assert len(pair) >= 1, f"Expected to find sanitized pair, got: {[d for d in data if 'apple' in d.get('word1', '').lower()]}"
	# Weight should be 3 (1 + 2 merged)
	assert pair[0]["weight"] == 3, f"Expected weight 3 (merged), got {pair[0]['weight']}"


def test_character_sanitization_curly_braces_brackets():
	"""Test removal of braces, brackets, and other special chars."""
	client = TestClient(app)

	unique = str(uuid.uuid4())[:8]
	alpha_unique = ''.join(c for c in unique if c.isalpha())
	
	# Payload with various special characters
	payload = [
		{"word1": f"{{apple}}{unique}", "word2": f"[fruit]{unique}", "weight": 1},
		{"word1": f"(apple){unique}", "word2": f"%fruit%{unique}", "weight": 1},
	]

	resp = client.post("/api/lemma_matrix/connections", json=payload)
	assert resp.status_code == 200

	# Fetch and verify
	list_resp = client.get("/api/lemma_matrix/connections?skip=0&limit=500")
	assert list_resp.status_code == 200
	data = list_resp.json()
	
	# All braces/brackets/percent/numbers should be removed
	# Both should normalize to apple{alpha_unique} and fruit{alpha_unique}
	pair = [d for d in data if d.get("word1") == f"apple{alpha_unique}" and d.get("word2") == f"fruit{alpha_unique}"]
	assert len(pair) >= 1, f"Expected to find sanitized pair with braces/brackets removed"
	# Both should merge (weights 1+1 = 2)
	assert pair[0]["weight"] == 2


def test_character_sanitization_preserves_spaces_between_words():
	"""Test that spaces between actual words are preserved."""
	client = TestClient(app)

	unique = str(uuid.uuid4())[:8]
	alpha_unique = ''.join(c for c in unique if c.isalpha())

	# Multi-word input: "hello world 123" should become "hello world" (no numbers)
	payload = [
		{"word1": f"hello world 123-{unique}", "word2": f"test phrase.{unique}", "weight": 1}
	]

	resp = client.post("/api/lemma_matrix/connections", json=payload)
	assert resp.status_code == 200

	# Fetch and verify
	list_resp = client.get("/api/lemma_matrix/connections?skip=0&limit=500")
	assert list_resp.status_code == 200
	data = list_resp.json()
	
	# Should preserve spaces between words, remove numbers/dashes
	# "hello world 123-{unique}" → "hello world {alpha_unique}"
	pair = [d for d in data if d.get("word1") == f"hello world {alpha_unique}"]
	assert len(pair) >= 1, f"Expected to find pair with preserved spaces, got: {[d for d in data if 'hello' in d.get('word1', '').lower()]}"


def test_build_and_upsert_increments_weights():
	client = TestClient(app)

	unique = str(uuid.uuid4())[:8]
	alpha_unique = ''.join(c for c in unique if c.isalpha())
	
	a = f"apple{alpha_unique}"  # Use alpha-only unique for consistency
	b = f"banana{alpha_unique}"

	text = f"{a} {b} {a}"

	# First build+upsert: should create a single pair a<->b with weight 2
	resp1 = client.post("/api/lemma_matrix/build_and_upsert", json={"text": text})
	assert resp1.status_code == 200
	body1 = resp1.json()
	assert isinstance(body1, dict) and "processed" in body1.get("message", ""), body1

	# Fetch matrix connections and find the pair
	list_resp = client.get("/api/lemma_matrix/connections?skip=0&limit=500")
	assert list_resp.status_code == 200
	data = list_resp.json()
	assert isinstance(data, list)
	assert len(data) >= 1, "Expected to find at least one connection after first upsert"

	pair = data[0]
	stored_a = pair["word1"]
	stored_b = pair["word2"]
	initial_weight = pair["weight"]
	assert initial_weight >= 1, f"Initial weight should be >=1, got {initial_weight}"

	# Second build+upsert: should increment the existing weight by the same amount
	resp2 = client.post("/api/lemma_matrix/build_and_upsert", json={"text": text})
	assert resp2.status_code == 200
	body2 = resp2.json()
	assert isinstance(body2, dict) and "processed" in body2.get("message", ""), body2

	# Fetch again and verify weight increased
	list_resp2 = client.get("/api/lemma_matrix/connections?skip=0&limit=500")
	assert list_resp2.status_code == 200
	data2 = list_resp2.json()

	pair_after = [d for d in data2 if d.get("word1") == stored_a and d.get("word2") == stored_b]
	assert len(pair_after) >= 1, f"Expected to find connection {stored_a} -> {stored_b} after second upsert"
	updated_weight = pair_after[0]["weight"]
	assert updated_weight >= initial_weight, f"Updated weight {updated_weight} should be >= initial {initial_weight}"
	assert updated_weight != initial_weight, "Weight should have changed after second upsert"

	# Expect the weight to have approximately doubled for this simple single-document test
	# (cooccurrence for 'a' and 'b' in "a b a" is 2 per build). Allow >= check to be robust.
	assert updated_weight >= initial_weight * 2 or updated_weight == initial_weight + 1



def test_real_world_text_sol_article():
	"""Test with real-world text about Sol from ancient Roman religion."""
	client = TestClient(app)
	
	text = """Sol is the personification of the Sun and a god in ancient Roman religion. It was long thought that Rome actually had two different, consecutive sun gods: The first, Sol Indiges (Latin: the deified sun), was thought to have been unimportant, disappearing altogether at an early period. Only in the late Roman Empire, scholars argued, did the solar cult re-appear with the arrival in Rome of the Syrian Sol Invictus (Latin: the unconquered sun), perhaps under the influence of the Mithraic mysteries.[1] Publications from the mid-1990s have challenged the notion of two different sun gods in Rome, pointing to the abundant evidence for the continuity of the cult of Sol, and the lack of any clear differentiation – either in name or depiction – between the "early" and "late" Roman sun god.[2][3][4][5]"""
	
	# Build and upsert from text
	resp = client.post("/api/lemma_matrix/build_and_upsert", json={"text": text})
	assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"
	body = resp.json()
	print(f"\nBuild response: {body}")
	
	# Verify response indicates pairs were created
	assert "processed" in body.get("message", ""), f"Expected 'processed' in message, got: {body}"
	
	# Extract count from message to know how many were created
	message = body.get("message", "")
	match = re.search(r'(\d+) created', message)
	assert match, f"Could not extract created count from message: {message}"
	created_count = int(match.group(1))
	print(f"Pairs created in this build: {created_count}")
	
	# Fetch all pairs (use max limit of 500)
	list_resp = client.get("/api/lemma_matrix/connections?skip=0&limit=500")
	assert list_resp.status_code == 200
	data = list_resp.json()
	assert isinstance(data, list)
	assert len(data) > 0, "Expected at least one pair to be created"
	
	# Filter for pairs from SOL article (look for keywords like "sol", "rome", "sun", "god", "cult", etc.)
	# These words appear in the article and shouldn't have dashes/numbers if properly sanitized
	sol_keywords = ["sol", "rome", "sun", "god", "cult", "empire", "believed", "solar"]
	sol_pairs = [d for d in data 
		if (any(kw in d.get("word1", "").lower() for kw in sol_keywords) or
		    any(kw in d.get("word2", "").lower() for kw in sol_keywords)) and
		   d.get("word1") and d.get("word2")]
	
	assert len(sol_pairs) > 0, f"Expected to find pairs containing Sol article keywords. Total pairs: {len(data)}"
	
	print(f"\nPairs containing Sol article keywords: {len(sol_pairs)}")
	print(f"Sample Sol article pairs (first 15):")
	for pair in sol_pairs[:15]:
		print(f"  '{pair['word1']}' <-> '{pair['word2']}' : weight={pair['weight']}")
	
	# Verify normalization on these pairs: no numbers or special characters in stored words
	for pair in sol_pairs:
		word1 = pair["word1"]
		word2 = pair["word2"]
		# Check no numbers in words
		assert not any(c.isdigit() for c in word1), f"Found digit in word1: {word1}"
		assert not any(c.isdigit() for c in word2), f"Found digit in word2: {word2}"
		# Check only alphabetic characters and spaces
		assert all(c.isalpha() or c.isspace() for c in word1), f"Found non-alpha char in word1: {word1}"
		assert all(c.isalpha() or c.isspace() for c in word2), f"Found non-alpha char in word2: {word2}"
		# Check all lowercase
		assert word1 == word1.lower(), f"word1 not lowercase: {word1}"
		assert word2 == word2.lower(), f"word2 not lowercase: {word2}"
		# Check stripped
		assert word1 == word1.strip(), f"word1 not stripped: '{word1}'"
		assert word2 == word2.strip(), f"word2 not stripped: '{word2}'"
		# Check weights are positive
		assert pair["weight"] >= 1, f"Expected weight >= 1, got {pair['weight']}"
	
	# Test that upserting the same text again increments weights
	resp2 = client.post("/api/lemma_matrix/build_and_upsert", json={"text": text})
	assert resp2.status_code == 200
	
	# Fetch pairs again
	list_resp2 = client.get("/api/lemma_matrix/connections?skip=0&limit=500")
	assert list_resp2.status_code == 200
	data2 = list_resp2.json()
	
	# Filter again
	sol_pairs2 = [d for d in data2 
		if (any(kw in d.get("word1", "").lower() for kw in sol_keywords) or
		    any(kw in d.get("word2", "").lower() for kw in sol_keywords)) and
		   d.get("word1") and d.get("word2")]
	
	# Verify weights have incremented for the original pairs
	for old_pair in sol_pairs:
		new_pair = [d for d in sol_pairs2 
			if d["word1"] == old_pair["word1"] and d["word2"] == old_pair["word2"]]
		assert len(new_pair) > 0, f"Pair not found: {old_pair}"
		new_weight = new_pair[0]["weight"]
		old_weight = old_pair["weight"]
		assert new_weight > old_weight, f"Weight should increase: {old_weight} -> {new_weight}"
	
	print(f"\n✓ All {len(sol_pairs)} Sol article pairs verified!")
	print("✓ Normalization and character sanitization working correctly")
	print("✓ Weights properly incremented on second upsert")
	print("✓ Test passed: real-world text processed, normalized, and upserted successfully")


def test_build_upsert_endpoint():
	"""Verify that the /api/lemma_matrix/build_upsert endpoint works successfully."""
	client = TestClient(app)
	text = "Sol is the personification of the Sun and a god in ancient Roman religion."
	resp = client.post("/api/lemma_matrix/build_and_upsert", json={"text": text})
	assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"
	body = resp.json()
	assert "processed" in body.get("message", "")


def test_build_upsert_endpoint_lenient_json():
	"""Verify that the /api/lemma_matrix/build_upsert endpoint parses malformed JSON with unescaped quotes."""
	client = TestClient(app)
	# Raw JSON string where the quotes inside "text" are NOT escaped
	raw_body = '{"text": "This has unescaped "quotes" and works fine."}'
	resp = client.post(
		"/api/lemma_matrix/build_and_upsert",
		content=raw_body,
		headers={"Content-Type": "application/json"}
	)
	assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
	body = resp.json()
	assert "processed" in body.get("message", "")


def test_sliding_window_cooccurrence():
	"""Verify that co-occurrences are only counted within the sliding window, not document-wide."""
	from Libs.Lemmatizer.lemma_matrix import LemmaMatrixBuilder

	builder = LemmaMatrixBuilder(window_size=2)
	
	# simple text: "apple banana cherry date elderberry"
	text = "apple banana cherry date elderberry"
	
	vectorizer, matrix = builder.build_cooccurrence_matrix([text])
	pairs = builder.extract_matrix_pairs(matrix, vectorizer)
	
	# Collect all words "apple" co-occurs with
	apple_pairs = [p for p in pairs if p["word1"] == "apple" or p["word2"] == "apple"]
	cooc_words = set()
	for p in apple_pairs:
		cooc_words.add(p["word1"])
		cooc_words.add(p["word2"])
	cooc_words.discard("apple")
	
	# Should co-occur with words within window_size=2
	assert "banana" in cooc_words
	assert "cherry" in cooc_words
	# Should NOT co-occur with words outside window_size=2
	assert "date" not in cooc_words
	assert "elderberry" not in cooc_words


def test_overwrite_and_clear_endpoints():
	"""Verify overwrite=True overwrites instead of accumulating weight, and DELETE endpoint clears data."""
	client = TestClient(app)
	
	# Clean database
	resp_del = client.delete("/api/lemma_matrix/connections")
	assert resp_del.status_code == 200
	
	text = "apple banana"
	
	# First build: weight is 1
	resp1 = client.post("/api/lemma_matrix/build_and_upsert", json={"text": text, "window_size": 1})
	assert resp1.status_code == 200
	
	# Query connections and verify weight is 1
	resp_get1 = client.get("/api/lemma_matrix/connections")
	assert resp_get1.status_code == 200
	conns1 = resp_get1.json()
	assert len(conns1) == 1
	assert conns1[0]["weight"] == 1
	
	# Second build without overwrite: weight accumulates to 2
	resp2 = client.post("/api/lemma_matrix/build_and_upsert", json={"text": text, "window_size": 1, "overwrite": False})
	assert resp2.status_code == 200
	conns2 = client.get("/api/lemma_matrix/connections").json()
	assert conns2[0]["weight"] == 2
	
	# Third build with overwrite=True: weight goes back to 1
	resp3 = client.post("/api/lemma_matrix/build_and_upsert", json={"text": text, "window_size": 1, "overwrite": True})
	assert resp3.status_code == 200
	conns3 = client.get("/api/lemma_matrix/connections").json()
	assert conns3[0]["weight"] == 1
	
	# Clear database via DELETE and verify it's empty
	resp_clear = client.delete("/api/lemma_matrix/connections")
	assert resp_clear.status_code == 200
	conns_empty = client.get("/api/lemma_matrix/connections").json()
	assert len(conns_empty) == 0





