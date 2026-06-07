from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Any

from Libs.Config.config import PAGE_DATABASE_PATH, LEMMA_DATABASE_PATH
from backend.database import  init_db
from backend.database.orm_schema_pages import PAGES_METADATA
from backend.database.orm_schema_lemmas import LEMMAS_METADATA


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Executes prior to the first incoming request
    page_engine, page_session = init_db.init_db(db_path=PAGE_DATABASE_PATH, metadata=PAGES_METADATA)
    lemma_engine, lemma_session = init_db.init_db(db_path=LEMMA_DATABASE_PATH, metadata=LEMMAS_METADATA)
    _app.state.page_engine = page_engine
    _app.state.page_session_factory = page_session
    _app.state.lemma_engine = lemma_engine
    _app.state.lemma_session_factory = lemma_session
    yield
    # Execute cleanup procedures here (e.g., engine disposal)


def _get_session_from_state(state_attr: str, db_path, metadata, engine_attr: str):
    session_factory: Any | None = getattr(app.state, state_attr, None)
    if session_factory is None:
        engine, session_factory = init_db.init_db(db_path=db_path, metadata=metadata)
        setattr(app.state, engine_attr, engine)
        setattr(app.state, state_attr, session_factory)
    if session_factory is None:
        raise RuntimeError(f"{state_attr} is not initialized")
    with session_factory() as session:
        yield session


def get_session():
    yield from _get_session_from_state(
        "page_session_factory",
        PAGE_DATABASE_PATH,
        PAGES_METADATA,
        "page_engine",
    )


def get_lemma_session():
    yield from _get_session_from_state(
        "lemma_session_factory",
        LEMMA_DATABASE_PATH,
        LEMMAS_METADATA,
        "lemma_engine",
    )


app = FastAPI(
    title="API",
    description="FastAPI with SQLite",
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
from backend.api import page_endpoints, lemma_endpoints, health_endpoints  # noqa: F401
