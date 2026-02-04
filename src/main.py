from fastapi import (
    FastAPI,
    Request,
    status,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_csrf_protect.flexible import CsrfProtect
from contextlib import asynccontextmanager

from src.dependencies.database import init_db
from src.dependencies.config import Config, EnvType, get_config, CSRFSettings

from src.routers import admin, public

templates = Jinja2Templates(directory="src/templates")


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


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context={"request": request},
        status_code=status.HTTP_404_NOT_FOUND,
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return templates.TemplateResponse(
        request=request,
        name="500.html",
        context={"request": request},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


app.mount(path="/static", app=StaticFiles(directory="src/static"), name="static")
app.mount(
    path="/uploads",
    app=StaticFiles(directory="uploads"),
    name="uploads",
)
