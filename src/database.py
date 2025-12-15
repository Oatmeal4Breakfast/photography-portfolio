from typing import Annotated, Generator
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker
from src.models.models import Base
from src.config import DBConfig, EnvType
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent


def _build_db_uri(config: DBConfig) -> str:
    "Build the db uri"
    if config.env_type == EnvType.DEVELOPMENT:
        if config.db_uri.startswith("sqlite:///"):
            db_file_path = config.db_uri.replace("sqlite:///", "")
            db_absolute_path = PROJECT_ROOT / db_file_path
            db_absolute_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_absolute_path}"
        else:
            raise ValueError(f"{config.db_uri} is not a valid path.")

    elif config.env_type == EnvType.PRODUCTION:
        if config.db_uri.startswith("postgres://"):
            db_uri = config.db_uri.replace("postgres://", "postgresql+psycopg://")
            return db_uri
        elif config.db_uri.startswith("postgresql://"):
            db_uri = config.db_uri.replace("postgresql", "postgresql+psycopg")
            return db_uri
        else:
            raise ValueError(f"{config.db_uri} is not postgres uri.")
    else:
        raise ValueError("Invalid db_uri")


def _create_db_engine(db_uri: str) -> Engine:
    """create an engine"""
    return create_engine(db_uri, connect_args={"check_same_thread": False})


config = DBConfig.from_env()
db_uri = _build_db_uri(config)
engine = _create_db_engine(db_uri)
SessionLocal = sessionmaker(engine)


def init_db() -> None:
    """Initialize all of the tables for db"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Generator function to yield a db session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _override_engine_for_tests(test_engine: Engine) -> None:
    """Override the engine with a test_engine for testing purposes"""
    global engine, SessionLocal
    engine = test_engine
    SessionLocal = sessionmaker(engine)
