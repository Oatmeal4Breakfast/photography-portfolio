from typing import Annotated, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from src.models.models import Base
from src.config import DBConfig, EnvType
from pathlib import Path


config = DBConfig.from_env()

PROJECT_ROOT = Path(__file__).parent.parent

if config.env_type == EnvType.DEVELOPMENT:
    if config.db_uri.startswith("sqlite:///"):
        db_file_path = config.db_uri.replace("sqlite:///", "")

        db_absolute_path = PROJECT_ROOT / db_file_path

        db_absolute_path.parent.mkdir(parents=True, exist_ok=True)

        db_url: str = f"sqlite:///{db_absolute_path}"

    else:
        raise ValueError(f"{config.db_uri} is not a valid path")

else:
    db_url: str = config.db_uri

engine = create_engine(db_url, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
