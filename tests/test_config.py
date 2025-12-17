import pytest
import os
from unittest.mock import patch
from src.config import Config, EnvType


class TestConfig:
    def test_from_env_success_development(self):
        with patch.dict(
            os.environ,
            {"DB_URI": "sqlite:///inventory/database.db", "ENV_TYPE": "development"},
        ):
            config = Config.from_env()
            assert config.db_uri == "sqlite:///inventory/database.db"
            assert config.env_type == EnvType.DEVELOPMENT

    def test_from_env_success_production(self):
        with patch.dict(
            os.environ,
            {"DB_URI": "postgresql://some_url_here", "ENV_TYPE": "production"},
        ):
            config = Config.from_env()
            assert config.db_uri == "postgresql://some_url_here"
            assert config.env_type == EnvType.PRODUCTION

    def test_env_production_replacement(self):
        with patch.dict(
            os.environ, {"DB_URI": "postgres://some_url_here", "ENV_TYPE": "production"}
        ):
            config = Config.from_env()
            assert config.db_uri == "postgres://some_url_here"
            assert config.env_type == EnvType.PRODUCTION

    def test_null_db_uri_env(self):
        with patch.dict(os.environ, {"ENV_TYPE": "development"}, clear=True):
            with pytest.raises(ValueError, match="Missing env variables"):
                Config.from_env()

    def test_null_env_type_env(self):
        with patch.dict(
            os.environ, {"DB_URI": "sqlite:///inventory/database.db"}, clear=True
        ):
            with pytest.raises(ValueError, match="Missing env variables"):
                Config.from_env()

    def test_invalid_env_type(self):
        with patch.dict(
            os.environ,
            {"DB_URI": "sqlite:///inventory/database.db", "ENV_TYPE": "staging"},
        ):
            with pytest.raises(ValueError, match="staging is not a valid type"):
                Config.from_env()


class TestEnvType:
    def test_enum_values(self):
        assert EnvType.PRODUCTION.value == "production"
        assert EnvType.DEVELOPMENT.value == "development"

    def test_enum_from_string(self):
        assert EnvType("production") == EnvType.PRODUCTION
        assert EnvType("development") == EnvType.DEVELOPMENT

    def test_enum_invalid_value(self):
        with pytest.raises(ValueError):
            EnvType("staging")
