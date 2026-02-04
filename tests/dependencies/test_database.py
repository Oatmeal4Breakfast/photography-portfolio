import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, inspect, text

from src.dependencies.config import Config, EnvType
from src.dependencies.database import (
    init_db,
    get_db,
    _build_db_uri,
    _create_db_engine,
    _override_engine_for_tests,
)

from src.models.schema import Base


@pytest.fixture()
def test_engine():
    engine_ = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_)
    return engine_


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
        config = MagicMock(spec=Config)
        config.env_type = EnvType.DEVELOPMENT
        config.db_uri = "sqlite:///test.db"

        with patch("src.dependencies.database.PROJECT_ROOT", tmp_path):
            result = _build_db_uri(config)

            assert result.startswith("sqlite:///")
            assert str(tmp_path) in result
            assert "test.db" in result

    def test_development_sqlite_creates_nested_directorys(self, tmp_path):
        config = MagicMock(spec=Config)
        config.env_type = EnvType.DEVELOPMENT
        config.db_uri = "sqlite:///data/nested/test.db"

        with patch("src.dependencies.database.PROJECT_ROOT", tmp_path):
            _build_db_uri(config)

            expected_dir = tmp_path / "data" / "nested"
            assert expected_dir.exists()

    def test_development_sqlite_raises_error(self):
        config = MagicMock(spec=Config)
        config.env_type = EnvType.DEVELOPMENT
        config.db_uri = "postgres://local_host"

        with pytest.raises(ValueError, match=f"{config.db_uri} is not a valid path."):
            _build_db_uri(config)

    def test_production_postgres_appends_psycopg(self):
        config = MagicMock(spec=Config)
        config.env_type = EnvType.PRODUCTION
        config.db_uri = "postgres://localhost/database.db"

        results = _build_db_uri(config)
        assert results == "postgresql+psycopg://localhost/database.db"

    def test_production_postgresql_appends_psycopg(self):
        config = MagicMock(spec=Config)
        config.env_type = EnvType.PRODUCTION
        config.db_uri = "postgresql://localhost/database.db"

        results = _build_db_uri(config)

        assert results == "postgresql+psycopg://localhost/database.db"

    def test_production_nonpostgres_uri_raises_error(self):
        config = MagicMock(spec=Config)
        config.env_type = EnvType.PRODUCTION
        config.db_uri = "postgresss://localhost/database.db"

        with pytest.raises(ValueError, match=f"{config.db_uri} is not a postgres uri."):
            _build_db_uri(config)


class TestCreateEngine:
    def test_creates_valid_engine(self):
        engine = _create_db_engine("sqlite:///:memory:")

        assert engine is not None
        assert str(engine.url) == "sqlite:///:memory:"

    def test_create_engine_connection_args(self):
        engine = _create_db_engine("sqlite:///:memory:")

        assert engine is not None


class TestInitDb:
    def test_creates_all_tables(self, setup_test_db):
        init_db()

        inspector = inspect(setup_test_db)
        table_names = inspector.get_table_names()

        assert len(table_names) > 0

    def test_impodent(self, setup_test_db):
        init_db()
        init_db()

        inspector = inspect(setup_test_db)
        table_names = inspector.get_table_names()

        assert len(table_names) > 0


class TestGetDb:
    """Test the get_db function"""

    def test_yields_active_session(self, setup_test_db):
        """Test that get_db yields an active session"""
        gen = get_db()
        session = next(gen)

        assert session is not None
        assert session.is_active

        try:
            next(gen)
        except StopIteration:
            pass

    def test_closes_session_after_use(self, setup_test_db):
        """Test that session is closed after use"""
        gen = get_db()
        session = next(gen)

        try:
            next(gen)
        except StopIteration:
            pass

        assert not session.in_transaction()

    def test_closes_session_on_exception(self, setup_test_db):
        """Test that session closes even on exception"""
        gen = get_db()
        session = next(gen)

        try:
            gen.throw(Exception("Test exception"))
        except Exception:
            pass

        assert not session.in_transaction()

    def test_can_execute_queries(self, db_session):
        """Test that session can execute queries"""
        result = db_session.execute(text("SELECT 1 as num"))
        row = result.fetchone()

        assert row[0] == 1

    def test_multiple_sessions_independent(self, setup_test_db):
        """Test that multiple sessions are independent"""
        gen1 = get_db()
        session1 = next(gen1)

        gen2 = get_db()
        session2 = next(gen2)

        assert session1 is not session2

        # Cleanup
        for gen in [gen1, gen2]:
            try:
                next(gen)
            except StopIteration:
                pass
