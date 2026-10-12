import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from app.storage.store import Store
from app.services.study import StudyService


@pytest.fixture
def service(tmp_path, qapp):
    store = Store(tmp_path / "data")
    yield StudyService(store)
    store.close()


@pytest.fixture
def hierarchy(service):
    s = service.subject("Matemática Computacional")
    session = service.session(s["id"], "Limites")
    sub = service.subsession(s["id"], session["id"], "Limites indeterminados")
    return s, session, sub
