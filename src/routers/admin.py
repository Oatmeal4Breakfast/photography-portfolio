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

from src.services.photo_service import PhotoService, PhotoValidator

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
from src.config import Config


router: APIRouter = APIRouter(prefix="/admin", tags=["admin"])

templates = Jinja2Templates(directory="src/templates")


def get_photo_service(
    db: Session = Depends(get_db),
    config: Config = Config(),
) -> PhotoService:
    return PhotoService(db=db, config=config)


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
    service: Annotated[PhotoService, Depends(dependency=get_photo_service)],
):
    validator: PhotoValidator = PhotoValidator(file=file)

    file_data: bytes | None = await validator.validate()

    if file_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="file empty or too large"
        )

    service: PhotoService = PhotoService(db=db)
    file_name: str | None = file.filename

    photo = service.upload_photo(
        title=title, file_name=file_name, file_data=file_data, collection=collection
    )
    if photo is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server could not upload image",
        )

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
