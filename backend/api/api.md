# Pages API

FastAPI application for managing Pages with an SQLite database.

## Run

```bash
python -m uvicorn backend.api.api:app --reload --host 127.0.0.1 --port 8000
```

## Endpoints

### StructuredPages
- `POST /api/structured-pages` - Create a structured page
- `GET /api/structured-pages?skip=0&limit=100` - List structured pages
- `GET /api/structured-pages/{page_id}` - Get a structured page
- `PUT /api/structured-pages/{page_id}` - Update a structured page

### UnstructuredPages
- `POST /api/unstructured-pages` - Create an unstructured page
- `GET /api/unstructured-pages?skip=0&limit=100` - List unstructured pages
- `GET /api/unstructured-pages/{page_id}` - Get an unstructured page
- `PUT /api/unstructured-pages/{page_id}` - Update an unstructured page

### WikiPages
- `POST /api/wiki-pages` - Create a wiki page
- `GET /api/wiki-pages?skip=0&limit=100` - List wiki pages
- `GET /api/wiki-pages/{wiki_id}` - Get a wiki page
- `PUT /api/wiki-pages/{wiki_id}` - Update a wiki page

### Health
- `GET /health` - Health check

## Example requests

### Create a page
```bash
curl -X POST http://127.0.0.1:8000/api/pages \
  -H "Content-Type: application/json" \
  -d '{"raw_text": "Sample text"}'
```

### Create a structured page
```bash
curl -X POST http://127.0.0.1:8000/api/structured-pages \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Einstein developed relativity",
    "triplets": [["Einstein", "developed", "relativity"]]
  }'
```

### Create an unstructured page
```bash
curl -X POST http://127.0.0.1:8000/api/unstructured-pages \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Signal text",
    "predicted_output": "Output",
    "prediction_error": 0.05
  }'
```

### Create a wiki page
```bash
curl -X POST http://127.0.0.1:8000/api/wiki-pages \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Ada Lovelace",
    "body": "Ada Lovelace was a mathematician...",
    "categories": ["Mathematicians"],
    "sections": [{"heading": "Early life", "content": "..."}]
  }'
```

### Update a page
```bash
curl -X PUT http://127.0.0.1:8000/api/pages/{page_id} \
  -H "Content-Type: application/json" \
  -d '{"raw_text": "Updated text"}'
```

## API docs

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

---

# Pages API (FastAPI)

Minimal API for storing Pages, StructuredPages, UnstructuredPages, and WikiPages in SQLite.

## Quick start

```bash
python -m uvicorn backend.api.api:app --reload --host 127.0.0.1 --port 8090
```

## Smoke test

```bash
python -m backend.api.smoke_test
```

## Notes

- SQLite database path is configured in `Libs/Config/config.json`.
- API usage examples live in `backend/api/api.md`.

[//]: # (Anlaşılan şu ki page'lerle ilgili api'ler yazılacak)
[//]: # (page için db'ye bağlayalım)
[//]: # (kw search yapmayı deneyelim ama önce database işini halledelim)
