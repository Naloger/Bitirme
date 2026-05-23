from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Any
from backend.database import init_db

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Executes prior to the first incoming request
    init_db.init_db()
    yield
    # Execute cleanup procedures here (e.g., engine disposal)


def get_session():
    if init_db.SessionLocal is None:
        init_db.init_db()
    session_factory: Any | None = init_db.SessionLocal
    if session_factory is None:
        raise RuntimeError("SessionLocal is not initialized")
    with session_factory() as session:
        yield session


app = FastAPI(
    title="Pages API",
    description="FastAPI with SQLite for managing Pages",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=["*"],  # type: ignore
    allow_credentials=True,  # type: ignore
    allow_methods=["*"],  # type: ignore
    allow_headers=["*"],  # type: ignore
)

# Ensure endpoint decorators are registered with the app
from backend.api import endpoints  # noqa: F401
