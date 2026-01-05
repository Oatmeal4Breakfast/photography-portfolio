from typing import Annotated
from fastapi import (
    FastAPI,
    Depends,
    Request,
)
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from src.dependencies.database import init_db, get_db
from src.dependencies.config import Config, EnvType, get_config

from src.services.photo_service import PhotoService

from src.routers import admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    config: Config = Config()
    if config.env_type == EnvType.DEVELOPMENT:
        init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(router=admin.router)

app.mount(path="/static", app=StaticFiles(directory="src/static"), name="static")
app.mount(
    path="/uploads",
    app=StaticFiles(directory="uploads"),
    name="uploads",
)

templates = Jinja2Templates(directory="src/templates")


def get_photo_service(
    db: Session = Depends(get_db), config: Config = Depends(get_config)
) -> PhotoService:
    return PhotoService(db=db, config=config)


@app.get(path="/", response_class=HTMLResponse)
async def home(
    request: Request,
    service: Annotated[PhotoService, Depends(dependency=get_photo_service)],
):
    thumbnail_path: str | None = service.get_hero_photo()
    print(thumbnail_path)
    if thumbnail_path is None:
        thumbnail_path: str = "static/images/fallback_hero.jpeg"
    photo_path: str = service.build_photo_url(path=thumbnail_path)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "photo": photo_path},
    )
