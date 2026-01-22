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
    algorithm: str = Field(validation_alias="ALGORITHM")
    auth_token_expire_minute: int = Field(validation_alias="AUTH_TOKEN_EXPIRE_MINUTES")
    max_image_size: int = Field(validation_alias="MAX_IMAGE_SIZE")

    # boto3 config
    r2_account_id: str = Field(validation_alias="R2_ACCOUNT_ID")
    aws_access_key_id: str = Field(validation_alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(validation_alias="AWS_SECRET_ACCESS_KEY")
    bucket: str = Field(validation_alias="BUCKET")


class CSRFSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False, env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    secret_key: str = Field(validation_alias="CSRF")
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_key: str = "csrf_token"
    token_key: str = "token_key"


def get_config() -> Config:
    return Config()
