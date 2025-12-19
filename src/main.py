from typing import Annotated
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Request,
    Form,
    UploadFile,
    File,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from src.models.models import Photo
from src.database import init_db, get_db
from src.config import Config, EnvType
from src.services.image_processor import create_thumbnail, create_original
from src.services.crud import (
    add_photo,
)
from src.utils.file_utils import sanitize_file
from src.utils.hash import get_hash, photo_hash_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    config: Config = Config.from_env()
    if config.env_type == EnvType.DEVELOPMENT:
        init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.mount(path="/static", app=StaticFiles(directory="src/static"), name="static")

templates = Jinja2Templates(directory="src/templates")


@app.get(path="/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get(path="/admin/upload", response_class=HTMLResponse, name="upload_form")
async def upload_form(request: Request):
    return templates.TemplateResponse(request=request, name="upload.html")


@app.post(path="/admin/upload")
async def uploads_photo(
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    collection: Annotated[str, Form()],
    request: Request,
    db: Annotated[Session, Depends(dependency=get_db)],
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename or file not uploaded",
        )

    allowed_img_type: list[str] = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_img_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_img_type)}",
        )

    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024
    file_data: bytes = await file.read()

    if len(file_data) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"file too large. Max size {MAX_IMAGE_SIZE / (1024 * 1024)} MB",
        )

    if len(file_data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file"
        )

    if not title or not title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Title cannot be empty"
        )

    if len(title) > 50:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Title too long. Max: 50",
        )

    file_hash: str = get_hash(file_data=file_data)
    if photo_hash_exists(hash=file_hash, db=db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"file with hash: {file_hash} already exists",
        )
    file_name: str = sanitize_file(file_name=file.filename)

    try:
        thumbnail_path: str = create_thumbnail(file=file_data, file_name=file_name)
        original_img_path: str = create_original(file=file_data, file_name=file_name)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid image {e}"
        )

    except IOError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving image: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server error: {e}",
        )

    try:
        new_photo: Photo = Photo(
            title=title,
            hash=file_hash,
            file_name=file_name,
            original_path=original_img_path,
            thumbnail_path=thumbnail_path,
            collection=collection,
        )
        add_photo(photo=new_photo, db=db)
    except Exception:
        db.rollback()

    redirect_url = request.url_for("upload_form")
    return RedirectResponse(url=f"{redirect_url}?success=true", status_code=303)
