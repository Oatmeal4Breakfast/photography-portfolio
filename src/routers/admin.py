from typing import Annotated, Sequence
from sqlalchemy.orm import Session

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import (
    HTTPException,
    Request,
    Depends,
    Form,
    UploadFile,
    File,
    status,
)
from fastapi.templating import Jinja2Templates

from src.utils.file_utils import sanitize_file, build_photo_url, get_hash

from src.services.photo_service import PhotoService

from src.services.crud import (
    add_photo,
    get_all_photos,
    get_photo_by_id,
    delete_photo_from_db,
    photo_hash_exists,
)
from src.services.image_processor import (
    create_original,
    create_thumbnail,
    delete_from_image_store,
)

from src.models.schema import Photo
from src.models.models import DeletePhotoPayload

from src.database import get_db


router: APIRouter = APIRouter(prefix="/admin", tags=["admin"])

templates = Jinja2Templates(directory="src/templates")


@router.get(path="/", response_class=HTMLResponse, name="login_form")
async def login_form(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@router.get(path="/upload", response_class=HTMLResponse, name="upload_form")
async def upload_form(request: Request):
    return templates.TemplateResponse(request=request, name="upload.html")


@router.post(path="/upload")
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

    service: PhotoService = PhotoService(db=db)

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

    if service.photo_hash_exists(hash=file_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"file with hash: {file_hash} already exists",
        )
    file_name: str = sanitize_file(file_name=file.filename)

    try:
        thumbnail_path: str = service.create_thumbnail(
            file=file_data, file_name=file_name
        )
        original_img_path: str = service.create_original(
            file=file_data, file_name=file_name
        )

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
        service.add_photo(photo=new_photo)
    except Exception:
        db.rollback()

    redirect_url = request.url_for("upload_form")
    return RedirectResponse(url=f"{redirect_url}?success=true", status_code=303)


@router.get(path="/photos")
async def view_photos(
    request: Request, db: Annotated[Session, Depends(dependency=get_db)]
):
    photos: Sequence[Photo] = get_all_photos(db=db)
    if len(photos) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Could not find photos.",
        )

    image_data: list[dict[str, str | int]] = []
    for photo in photos:
        path: str | None = build_photo_url(path=photo.thumbnail_path)
        photo
        if path is None:
            image_data.append({"id": photo.id, "path": ""})
        else:
            image_data.append({"id": photo.id, "path": path})

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"request": request, "photos": image_data},
    )


@router.post(path="/photos/delete")
async def delete_photos(
    payload: DeletePhotoPayload, db: Annotated[Session, Depends(dependency=get_db)]
):
    photo_ids: list[int] = payload.photo_ids
    if not photo_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No photos selected",
        )

    for photo_id in photo_ids:
        photo: Photo | None = get_photo_by_id(id=photo_id, db=db)
        if photo is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Photo not found in db",
            )
        try:
            delete_photo_from_db(photo=photo, db=db)
            delete_from_image_store(
                photo_paths=[photo.thumbnail_path, photo.original_path]
            )
        except Exception as e:
            raise Exception(f"Error: {e}")
