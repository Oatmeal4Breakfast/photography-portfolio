from fastapi import (
    FastAPI,
)
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from src.dependencies.database import init_db
from src.dependencies.config import Config, EnvType, get_config

from src.routers import admin, public


@asynccontextmanager
async def lifespan(app: FastAPI):
    config: Config = get_config()
    if config.env_type == EnvType.DEVELOPMENT:
        init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(router=public.router)
app.include_router(router=admin.router)

app.mount(path="/static", app=StaticFiles(directory="src/static"), name="static")
app.mount(
    path="/uploads",
    app=StaticFiles(directory="uploads"),
    name="uploads",
)
