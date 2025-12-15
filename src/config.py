from dataclasses import dataclass
from dotenv import load_dotenv
from enum import Enum
from typing import Self
import os


load_dotenv()


class EnvType(Enum):
    PRODUCTION = "production"
    DEVELOPMENT = "development"


@dataclass
class DBConfig:
    db_uri: str
    env_type: EnvType

    @classmethod
    def from_env(cls) -> Self:
        db_uri = os.getenv("DB_URI")
        env_type_str = os.getenv("ENV_TYPE")

        if db_uri is None or env_type_str is None:
            raise ValueError("Missing env variables")

        assert db_uri is not None
        assert env_type_str is not None

        try:
            env_type = EnvType(env_type_str)
        except ValueError:
            raise ValueError(
                f"{env_type_str} is not a valid type for the environment variable"
            )

        # if env_type == EnvType.PRODUCTION:
        #     if db_uri.startswith("postgres://"):
        #         db_uri = db_uri.replace("postgres://", "postgresql+psycopg://")

        return cls(db_uri, env_type)
