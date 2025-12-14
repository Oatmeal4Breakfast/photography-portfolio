from fastapi import FastAPI, Depends, HTTPException
from fastapi import templating
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from contextlib import asynccontextmanager

from src.models.models import Photo, Comment, User
from src.database import init_db, get_db
from src.config import DBConfig, EnvType


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = DBConfig.from_env()
    if config.env_type == EnvType.DEVELOPMENT:
        init_db()

    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
