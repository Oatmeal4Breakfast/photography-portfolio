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
class Config:
    db_uri: str
    env_type: EnvType
    image_store_url: str

    @classmethod
    def from_env(cls) -> Self:
        db_uri: str | None = os.getenv(key="DB_URI")
        env_type_str: str | None = os.getenv(key="ENV_TYPE")
        image_store_url: str | None = os.getenv(key="IMAGE_STORE_BASE_URL")

        missing_vars: list[str] = []

        if db_uri is None:
            missing_vars.append("db_uri")
        if env_type_str is None:
            missing_vars.append("missing_vars")
        if image_store_url is None:
            missing_vars.append("image_store_url")

        if missing_vars:
            raise ValueError("Missing env variables")

        assert db_uri is not None
        assert env_type_str is not None
        assert image_store_url is not None

        try:
            env_type = EnvType(value=env_type_str)
        except ValueError:
            raise ValueError(
                f"{env_type_str} is not a valid type for the environment variable"
            )

        # if env_type == EnvType.PRODUCTION:
        #     if db_uri.startswith("postgres://"):
        #         db_uri = db_uri.replace("postgres://", "postgresql+psycopg://")

        return cls(db_uri, env_type, image_store_url)
