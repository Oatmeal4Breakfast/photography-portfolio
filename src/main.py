from fastapi import (
    FastAPI,
)
from fastapi.staticfiles import StaticFiles
from fastapi_csrf_protect.flexible import CsrfProtect
from contextlib import asynccontextmanager

from src.dependencies.database import init_db
from src.dependencies.config import Config, EnvType, get_config, CSRFSettings

from src.routers import admin, public


@CsrfProtect.load_config
def get_csrf_config() -> CSRFSettings:
    return CSRFSettings()


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
