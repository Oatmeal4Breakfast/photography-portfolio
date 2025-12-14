import pytest
import os
from unittest.mock import patch
from src.config import DBConfig, EnvType


class TestDBConfig:
    def test_from_env_success_development(self):
        with patch.dict(
            os.environ,
            {"DB_URI": "sqlite:///inventory/database.db", "ENV_TYPE": "development"},
        ):
            config = DBConfig.from_env()
            assert config.db_uri == "sqlite:///inventory/database.db"
            assert config.env_type == EnvType.DEVELOPMENT
