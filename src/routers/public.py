from typing import Annotated, Sequence

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import HTTPException, Request, Depends
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from src.services.photo_service import PhotoService

from src.models.schema import Photo

from src.dependencies.database import get_db
from src.dependencies.config import get_config, Config


router: APIRouter = APIRouter()

templates = Jinja2Templates(directory="src/templates")


def get_photo_service(
    db: Session = Depends(get_db), config: Config = Depends(get_config)
) -> PhotoService:
    return PhotoService(db=db, config=config)


@router.get(path="/", response_class=HTMLResponse)
async def home(
    request: Request, service: Annotated[PhotoService, Depends(get_photo_service)]
):
    """Home page for the site"""

    image: str | None = service.get_hero_photo()

    if image is None:
        image: str = "static/images/fallback_hero.jpeg"

    photo_path: str = service.build_photo_url(path=image)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "photo": photo_path},
    )


@router.get(path="/about", response_class=HTMLResponse)
async def about(
    request: Request, service: Annotated[PhotoService, Depends(get_photo_service)]
):
    image: str | None = service.get_about_image()
    photo_path: str = service.build_photo_url(path=image)
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={"request": request, "photo": photo_path},
    )
