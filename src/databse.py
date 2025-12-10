from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from models.base import Base
from config import DBConfig
from pathlib import Path


config = DBConfig().from_env()

db_path = Path(config.file_name)
db_path.parent.mkdir(parents=True, exist_ok=True)

sqlite_url: str = f"sqlite:///{config.file_name}"

engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
