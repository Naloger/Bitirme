# FastAPI Guide & API Documentation

## Table of Contents
1. [General FastAPI Knowledge](#general-fastapi-knowledge)
2. [API Overview](#api-overview)
3. [Setup & Running](#setup--running)
4. [API Endpoints](#api-endpoints)
5. [Request/Response Examples](#requestresponse-examples)
6. [Error Handling](#error-handling)
7. [CORS Configuration](#cors-configuration)

---

## General FastAPI Knowledge

### What is FastAPI?

**FastAPI** is a modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints. It's built on top of **Starlette** for the web parts and **Pydantic** for the data parts.

### Key Features

- **Fast**: Very high performance, comparable to NodeJS and Go
- **Intuitive**: Great editor support with auto-completion and type hints
- **Easy**: Built to be easy to use and learn
- **Standards-based**: Based on open standards (OpenAPI and JSON Schema)
- **Automatic Documentation**: Built-in Swagger UI and ReDoc documentation
- **Async/Await Support**: Native async support for high concurrency
- **Dependency Injection**: Built-in dependency injection system

### Core Concepts

#### 1. **Decorators**
FastAPI uses decorators to define HTTP routes:
```python
@app.get("/path")          # GET request
@app.post("/path")         # POST request
@app.put("/path")          # PUT request
@app.delete("/path")       # DELETE request
@app.patch("/path")        # PATCH request
```

#### 2. **Path Parameters**
Dynamic URL segments captured as function parameters:
```python
@app.get("/items/{item_id}")
def get_item(item_id: str):
    return {"item_id": item_id}
```
- Access: `/items/123` → `item_id = "123"`

#### 3. **Query Parameters**
Parameters passed in the URL query string:
```python
@app.get("/items/")
def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```
- Access: `/items/?skip=0&limit=20`

#### 4. **Request Body**
Data sent in the request body (usually JSON):
```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float

@app.post("/items/")
def create_item(item: Item):
    return item
```

#### 5. **Response Models**
Define expected response structure using Pydantic models:
```python
@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: str):
    return {"name": "Item", "price": 9.99}
```
- FastAPI validates and serializes the response

#### 6. **Status Codes**
Specify response status codes:
```python
@app.post("/items/", status_code=201)
def create_item(item: Item):
    return item
```

#### 7. **Type Hints**
FastAPI uses Python type hints for:
- Input validation
- Automatic documentation
- Editor auto-completion
- Type checking

#### 8. **Exception Handling**
Built-in HTTP exceptions:
```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
def get_item(item_id: str):
    if not found:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```

#### 9. **CORS (Cross-Origin Resource Sharing)**
Allow requests from different origins:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"]   # Allow all headers
)
```

#### 10. **Lifespan Events**
Run code on application startup/shutdown:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code here
    print("Starting up")
    yield
    # Shutdown code here
    print("Shutting down")

app = FastAPI(lifespan=lifespan)
```

---

## API Overview

This API manages different types of pages stored in a SQLite database. It provides CRUD (Create, Read, Update) operations for four page types:

1. **Pages** - Basic pages with raw text and keywords
2. **StructuredPages** - Pages with extracted knowledge triplets
3. **UnstructuredPages** - Pages with predicted output and error tracking
4. **WikiPages** - Complex wiki-formatted pages with sections, references, links

### Key Information
- **Base URL**: `http://localhost:8000`
- **Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)
- **CORS**: Enabled for all origins
- **Database**: SQLite

---

## Setup & Running

### Prerequisites
```bash
pip install fastapi uvicorn pydantic
```

### Running the Server

#### Development (with auto-reload)
```bash
# From the backend directory
python -m uvicorn backend.api.api:app --reload --host 0.0.0.0 --port 8000
```

#### Production
```bash
# From the backend directory
python -m uvicorn backend.api.api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Parameters
- `--reload`: Restart server on code changes
- `--host`: Bind to specific host (0.0.0.0 = all interfaces)
- `--port`: Server port (default: 8000)
- `--workers`: Number of worker processes

### Accessing the API
- API: `http://localhost:8000`
- Swagger Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## API Endpoints

### Health Check

#### Check Server Status
```
GET /health
```
**Response:**
```json
{"status": "ok"}
```

---

### Pages Endpoints

#### Create a Page
```
POST /api/pages
Content-Type: application/json

{
  "raw_text": "The content of the page",
  "keywords": ["keyword1", "keyword2"]
}
```
**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "creation_timestamp": 1705142400.123,
  "raw_text": "The content of the page",
  "keywords": ["keyword1", "keyword2"],
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### Get All Pages
```
GET /api/pages?skip=0&limit=10
```
**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0, min: 0)
- `limit` (int, optional): Number of records to return (default: 100, min: 1, max: 1000)

**Response (200):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "creation_timestamp": 1705142400.123,
    "raw_text": "The content of the page",
    "keywords": ["keyword1", "keyword2"],
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

#### Get a Specific Page
```
GET /api/pages/{page_id}
```
**Path Parameters:**
- `page_id` (string): The UUID of the page

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "creation_timestamp": 1705142400.123,
  "raw_text": "The content of the page",
  "keywords": ["keyword1", "keyword2"],
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### Update a Page
```
PUT /api/pages/{page_id}
Content-Type: application/json

{
  "raw_text": "Updated content",
  "keywords": ["new_keyword"]
}
```
**Path Parameters:**
- `page_id` (string): The UUID of the page

**Request Body:** (all fields optional)
- `raw_text` (string): New page content
- `keywords` (array): New keywords list

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "creation_timestamp": 1705142400.123,
  "raw_text": "Updated content",
  "keywords": ["new_keyword"],
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-14T10:30:45"
}
```

---

### Structured Pages Endpoints

#### Create a Structured Page
```
POST /api/structured-pages
Content-Type: application/json

{
  "raw_text": "The content",
  "keywords": ["keyword1"],
  "triplets": [
    {"subject": "entity1", "predicate": "relation", "object": "entity2"}
  ]
}
```

#### Get All Structured Pages
```
GET /api/structured-pages?skip=0&limit=10
```

#### Get a Specific Structured Page
```
GET /api/structured-pages/{page_id}
```

#### Update a Structured Page
```
PUT /api/structured-pages/{page_id}
Content-Type: application/json

{
  "raw_text": "Updated content",
  "keywords": ["keyword1"],
  "triplets": []
}
```

---

### Unstructured Pages Endpoints

#### Create an Unstructured Page
```
POST /api/unstructured-pages
Content-Type: application/json

{
  "raw_text": "The content",
  "keywords": ["keyword1"],
  "predicted_output": "Some prediction",
  "prediction_error": 0.05
}
```

#### Get All Unstructured Pages
```
GET /api/unstructured-pages?skip=0&limit=10
```

#### Get a Specific Unstructured Page
```
GET /api/unstructured-pages/{page_id}
```

#### Update an Unstructured Page
```
PUT /api/unstructured-pages/{page_id}
Content-Type: application/json

{
  "raw_text": "Updated content",
  "keywords": ["keyword1"],
  "predicted_output": "Updated prediction",
  "prediction_error": 0.03
}
```

---

### Wiki Pages Endpoints

#### Create a Wiki Page
```
POST /api/wiki-pages
Content-Type: application/json

{
  "raw_text": "Wiki content",
  "keywords": ["keyword1"],
  "title": "Page Title",
  "body": "Main content",
  "sections": [
    {
      "heading": "Section 1",
      "content": "Section content"
    }
  ],
  "categories": ["Category1"],
  "infobox": {"field": "value"},
  "wikilinks": ["Link1", "Link2"],
  "interwiki_links": ["en:Page"],
  "external_links": ["http://example.com"],
  "see_also": ["Related1"],
  "references": [
    {
      "title": "Reference Title",
      "url": "http://ref.com"
    }
  ],
  "templates": ["Template1"],
  "disambiguation": []
}
```

#### Get All Wiki Pages
```
GET /api/wiki-pages?skip=0&limit=10
```

#### Get a Specific Wiki Page
```
GET /api/wiki-pages/{wiki_id}
```

#### Update a Wiki Page
```
PUT /api/wiki-pages/{wiki_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "body": "Updated body content"
  // other fields optional
}
```

---

## Request/Response Examples

### Using cURL

#### Create a Page
```bash
curl -X POST "http://localhost:8000/api/pages" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "This is a sample page",
    "keywords": ["sample", "page"]
  }'
```

#### Get All Pages
```bash
curl -X GET "http://localhost:8000/api/pages?skip=0&limit=5"
```

#### Get Specific Page
```bash
curl -X GET "http://localhost:8000/api/pages/550e8400-e29b-41d4-a716-446655440000"
```

#### Update a Page
```bash
curl -X PUT "http://localhost:8000/api/pages/550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Updated content",
    "keywords": ["updated"]
  }'
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Create a page
response = requests.post(f"{BASE_URL}/api/pages", json={
    "raw_text": "Sample content",
    "keywords": ["sample"]
})
page_id = response.json()["id"]

# Get all pages
response = requests.get(f"{BASE_URL}/api/pages", params={"skip": 0, "limit": 10})
pages = response.json()

# Get specific page
response = requests.get(f"{BASE_URL}/api/pages/{page_id}")
page = response.json()

# Update page
response = requests.put(f"{BASE_URL}/api/pages/{page_id}", json={
    "raw_text": "Updated content"
})
updated_page = response.json()
```

### Using JavaScript/Fetch

```javascript
const BASE_URL = "http://localhost:8000";

// Create a page
const createResponse = await fetch(`${BASE_URL}/api/pages`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    raw_text: "Sample content",
    keywords: ["sample"]
  })
});
const page = await createResponse.json();
const pageId = page.id;

// Get all pages
const listResponse = await fetch(`${BASE_URL}/api/pages?skip=0&limit=10`);
const pages = await listResponse.json();

// Get specific page
const getResponse = await fetch(`${BASE_URL}/api/pages/${pageId}`);
const pageData = await getResponse.json();

// Update page
const updateResponse = await fetch(`${BASE_URL}/api/pages/${pageId}`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    raw_text: "Updated content",
    keywords: ["updated"]
  })
});
const updatedPage = await updateResponse.json();
```

---

## Error Handling

### Standard HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Successful GET, PUT |
| 201 | Created | Successful POST |
| 400 | Bad Request | Invalid request data |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

### Error Response Format
```json
{
  "detail": "Page not found"
}
```

### Common Errors

#### 404 Not Found
```json
{"detail": "Page not found"}
```

#### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "raw_text"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## CORS Configuration

### Current Configuration
The API allows requests from any origin:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Allow all origins
    allow_credentials=True,     # Allow credentials
    allow_methods=["*"],        # Allow all HTTP methods
    allow_headers=["*"]         # Allow all headers
)
```

### Customizing CORS for Production

To restrict CORS to specific origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com", "https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"]
)
```

---

## Tips & Best Practices

### 1. Use Type Hints
Always use type hints for automatic validation and documentation.

### 2. Test with Swagger UI
Access `/docs` to test endpoints interactively during development.

### 3. Pagination
Always use `skip` and `limit` parameters when fetching large datasets.

### 4. Error Messages
Use descriptive error messages for better debugging.

### 5. Async When Possible
Use `async def` for endpoints to improve concurrency:
```python
@app.get("/api/pages")
async def get_pages():
    # Can now use await for I/O operations
    pass
```

### 6. Dependency Injection
Use FastAPI's dependency system for shared logic:
```python
async def get_query(q: str = Query(None)):
    return q

@app.get("/search")
async def search(query: str = Depends(get_query)):
    return {"query": query}
```

---

## Additional Resources

- [FastAPI Official Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Starlette Documentation](https://www.starlette.io/)
- [OpenAPI Specification](https://swagger.io/specification/)
