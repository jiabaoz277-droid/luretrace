"""测试配置：使用独立测试库，避免污染开发数据。"""
import os
import pathlib

_TEST_DB = pathlib.Path(__file__).resolve().parents[2] / "data" / "test_fishing.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import agent  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_state():
    from app.models import Base

    agent._sessions.clear()
    Base.metadata.drop_all(bind=db.get_engine())
    db.init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)
