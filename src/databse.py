from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from models.photo import Base
from config import DBConfig
from pathlib import Path


config = DBConfig.from_env()

# if config.env_type == EnvType.DEVELOPMENT:
#     db_path = Path(config.db_uri)
#     db_path.parent.mkdir(parents=True, exist_ok=True)


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
