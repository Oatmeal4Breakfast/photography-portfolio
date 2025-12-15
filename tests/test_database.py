import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from sqlalchemy import create_engine, inspect, text

from src.config import DBConfig, EnvType
from src.database import (
    init_db,
    get_db,
    _build_db_uri,
    _create_db_engine,
    _override_engine_for_tests,
)

from src.models.models import Base


@pytest.fixture()
def test_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture()
def setup_test_db(test_engine):
    _override_engine_for_tests(test_engine=test_engine)
    yield test_engine


@pytest.fixture()
def db_session(setup_test_db):
    gen = get_db()
    session = next(gen)
    yield session
    try:
        next(gen)
    except StopIteration:
        pass


class TestBuildUrl:
    def test_development_sqlite_creates_absolute_path(self, tmp_path):
        config = MagicMock(spec=DBConfig)
        config.env_type = EnvType.DEVELOPMENT
        config.db_uri = "sqlite:///test.db"

        with patch("src.database.PROJECT_ROOT", tmp_path):
            result = _build_db_uri(config)

            assert result.startswith("sqlite:///")
            assert str(tmp_path) in result
            assert "test.db" in result

    def test_development_sqlite_creates_nested_directorys(self, tmp_path):
        config = MagicMock(spec=DBConfig)
        config.env_type = EnvType.DEVELOPMENT
        config.db_uri = "sqlite:///data/nested/test.db"

        with patch("src.data.PROJECT_ROOT", tmp_path):
            _build_db_uri(config)

            expected_dir = tmp_path / "data" / "nested"
            assert expected_dir.exists()

    def test_development_sqlite_raises_error(self):
        config = MagicMock(spec=DBConfig)
        config.env_type = EnvType.DEVELOPMENT
        config.db_uri = "postgres://local_host"

        with pytest.raises(ValueError, f"{config.db_uri} is not a valid path."):
            _build_db_uri(config)
