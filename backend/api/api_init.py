from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Any

from Libs.Config.config import PAGE_DATABASE_PATH,  LEMMA_MATRIX_DATABASE_PATH
from backend.database import  init_db
from backend.database.ORMSchemas.orm_schema_pages import PAGES_METADATA
from backend.database.ORMSchemas.orm_schema_lemma_matrix import LEMMA_MATRIX_METADATA


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Executes prior to the first incoming request
    page_engine, page_session = init_db.init_db(db_path=PAGE_DATABASE_PATH, metadata=PAGES_METADATA)
    lemma_matrix_engine, lemma_matrix_session = init_db.init_db(db_path=LEMMA_MATRIX_DATABASE_PATH, metadata=LEMMA_MATRIX_METADATA)
    _app.state.page_engine = page_engine
    _app.state.page_session_factory = page_session
    _app.state.lemma_matrix_engine = lemma_matrix_engine
    _app.state.lemma_matrix_session_factory = lemma_matrix_session
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



def get_lemma_matrix_session():
    yield from _get_session_from_state(
        "lemma_matrix_session_factory",
        LEMMA_MATRIX_DATABASE_PATH,
        LEMMA_MATRIX_METADATA,
        "lemma_matrix_engine",
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
from backend.api.Endpoints import health_endpoints, page_endpoints, lemma_matrix_endpoints, spreading_activation_endpoints

app.include_router(health_endpoints.router)
app.include_router(page_endpoints.router)
app.include_router(lemma_matrix_endpoints.router, prefix="/api/lemma_matrix")
app.include_router(spreading_activation_endpoints.router, prefix="/api/lemma_matrix")
