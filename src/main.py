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

from src.database import init_db, get_db
from src.config import Config, EnvType
from src.services.crud import (
    get_hero_photo,
)
from src.utils.file_utils import build_photo_url

from src.routers import admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    config: Config = Config.from_env()
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


@app.get(path="/", response_class=HTMLResponse)
async def home(request: Request, db: Annotated[Session, Depends(dependency=get_db)]):
    thumbnail_path: str | None = get_hero_photo(db=db)
    if thumbnail_path is None:
        thumbnail_path: str = "/static/images/fallback_hero.jpeg"
    photo_path: str = build_photo_url(path=thumbnail_path)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "photo": photo_path},
    )
