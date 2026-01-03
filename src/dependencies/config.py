from enum import Enum
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class EnvType(Enum):
    PRODUCTION = "production"
    DEVELOPMENT = "development"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False, env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    db_uri: str = Field(validation_alias="DB_URI")
    env_type: EnvType = Field(validation_alias="ENV_TYPE")
    image_store: str = Field(validation_alias="IMAGE_STORE_BASE_URL")
    secret_key: str = Field(validation_alias="SECRET_KEY")
    alogrithm: str = Field(validation_alias="ALGORITHM")
    auth_token_expire_minute: int = Field(validation_alias="AUTH_TOKEN_EXPIRE_MINUTES")
    max_image_size: int = Field(validation_alias="MAX_IMAGE_SIZE")


def get_config() -> Config:
    config: Config = Config()
    return config
