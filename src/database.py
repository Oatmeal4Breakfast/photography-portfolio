from typing import Generator
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker
from src.models.models import Base
from src.config import Config, EnvType
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent


def _build_db_uri(config: Config) -> str:
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
            raise ValueError(f"{config.db_uri} is not a postgres uri.")
    else:
        raise ValueError("Invalid environment type")


def _create_db_engine(db_uri: str) -> Engine:
    """create an engine"""
    return create_engine(db_uri, connect_args={"check_same_thread": False})


config: Config = Config.from_env()
db_uri: str = _build_db_uri(config)
engine: Engine = _create_db_engine(db_uri)
SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine)


def init_db() -> None:
    """Initialize all of the tables for db"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Generator function to yield a db session"""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
