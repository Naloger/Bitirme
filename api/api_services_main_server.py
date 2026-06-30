from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.Agentic.MainAgents.SalienceMode.SalienceExecutor import (
    execute_salience_router_stream,
)

# Assuming your service function from the previous step is here

app = FastAPI(
    title="Salience Agent Gateway",
    description="API Gateway for routing and streaming Salience Graph node updates.",
    version="1.0.0"
)

class RouterRequest(BaseModel):
    user_input: str

@app.post(
    "/api/v1/agent/salience/stream",
    response_class=StreamingResponse, # Explicitly documents the response type
    summary="Stream Salience Router execution",
    description="Triggers the agent graph and outputs newline-delimited JSON events as they occur."
)
async def stream_salience_router(payload: RouterRequest):
    """
    Calls the underlying async service generator and streams the packets.
    """
    stream_generator = execute_salience_router_stream(user_input=payload.user_input)

    # application/x-ndjson tells clients each line is its own distinct JSON object
    return StreamingResponse(stream_generator, media_type="application/x-ndjson")
