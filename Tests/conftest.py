import pytest
from backend.api.api_init import  get_lemma_matrix_session, get_session
from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
    LemmaMatrixModel,
    VocabularyModel,
    PPMILemmaMatrixModel,
    ConceptsModel,
    ConceptConnectionsModel,
)
from backend.database.ORMSchemas.orm_schema_pages import (
    StructuredPageModel,
    UnstructuredPageModel,
    WikiPageModel,
)
from sqlmodel import delete

@pytest.fixture(autouse=True)
def clean_databases():
    # Clean lemma matrix database
    session_gen = get_lemma_matrix_session()
    session = next(session_gen)
    try:
        session.exec(delete(LemmaMatrixModel))
        session.exec(delete(PPMILemmaMatrixModel))
        session.exec(delete(ConceptConnectionsModel))
        session.exec(delete(ConceptsModel))
        session.exec(delete(VocabularyModel))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass

    # Clean page database
    session_gen_page = get_session()
    session_page = next(session_gen_page)
    try:
        session_page.query(StructuredPageModel).delete()
        session_page.query(UnstructuredPageModel).delete()
        session_page.query(WikiPageModel).delete()
        session_page.commit()
    except Exception:
        session_page.rollback()
    finally:
        try:
            next(session_gen_page)
        except StopIteration:
            pass
