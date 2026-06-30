"""
Frontend FastAPI application.

Serves the chat UI and proxies streaming requests to the Salience Agent API
so the browser avoids CORS issues.

Usage:
    uvicorn frontend.app:app --host 127.0.0.1 --port 8080 --reload
"""

import httpx
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel

SERVICES_API_BASE = "http://127.0.0.1:8100"

app = FastAPI(title="Salience Chat UI", version="1.0.0")

# Serve static assets (CSS, JS)
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ChatRequest(BaseModel):
    user_input: str


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main chat page."""
    html_path = Path(__file__).resolve().parent / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest):
    """
    Proxy the user message to the Salience Agent streaming endpoint
    and relay the NDJSON chunks back to the browser.
    """

    async def event_generator():
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            async with client.stream(
                "POST",
                f"{SERVICES_API_BASE}/api/v1/agent/salience/stream",
                json={"user_input": payload.user_input},
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        yield line + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
