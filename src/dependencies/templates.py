from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.dependencies.database import get_db
from src.dependencies.config import Config, get_config


templates = Jinja2Templates(directory="src/templates")


def get_collections_for_nav() -> list[str]:
    from src.services.photo_service import PhotoService

    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        config: Config = get_config()
        service = PhotoService(db, config)
        collections: list[str] = service.get_unique_collections()
        return [
            collection for collection in collections if collection not in ["about_me"]
        ]
    finally:
        db.close()


templates.env.globals["collections"] = get_collections_for_nav
