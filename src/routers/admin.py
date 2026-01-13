from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
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
    Cookie,
)
from fastapi.templating import Jinja2Templates
from fastapi_csrf_protect import CsrfProtect

from pydantic_settings import BaseSettings
from pydantic import Field

from src.services.photo_service import PhotoService, PhotoValidator
from src.services.user_service import AuthService

from src.models.schema import Photo, User
from src.models.models import DeletePhotoPayload, UserRegistration

from src.dependencies.database import get_db
from src.dependencies.config import get_config, Config


router: APIRouter = APIRouter(prefix="/admin", tags=["admin"])

templates = Jinja2Templates(directory="src/templates")


class CSRFSettings(BaseSettings):
    csrf_secret: str = Field(validation_alias="CSRF")
    cookie_samesite: str = "none"
    cookie_name: str = "csrf_token"


@CsrfProtect.load_config
def get_csrf_config() -> CSRFSettings:
    return CSRFSettings()


def get_photo_service(
    db: Session = Depends(get_db),
    config: Config = Depends(get_config),
) -> PhotoService:
    return PhotoService(db=db, config=config)


def get_auth_service(
    db: Session = Depends(get_db), config: Config = Depends(get_config)
) -> AuthService:
    return AuthService(db=db, config=config)


async def user_registration_form(
    firstname: Annotated[str, Form()],
    lastname: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> UserRegistration:
    """verify the form with a pydantic model"""
    return UserRegistration(
        firstname=firstname, lastname=lastname, email=email, password=password
    )


async def get_current_user(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> User | RedirectResponse:
    if not access_token:
        redirect_url = request.url_for("login_form")
        return RedirectResponse(url=redirect_url, status_code=303)
    token: str = access_token.replace("Bearer: ", "")
    user: User | None = service.verify_access_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access to the page. User not found",
        )
    return user


@router.get(path="/", response_class=HTMLResponse, name="login_form")
def login_form(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    csrf_protect: Annotated[CsrfProtect, Depends()],
):
    if not service.admin_exists():
        return RedirectResponse(
            url=request.url_for("registration_form"), status_code=303
        )
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(
        name="login.html", context={"request": request, "csrf_token": csrf_token}
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@router.post(path="/login")
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends(OAuth2PasswordRequestForm)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    csrf_protect: Annotated[CsrfProtect, Depends()],
):
    """Authenticate the user with the data from the form and set the session cookie"""
    await csrf_protect.validate_csrf(request)

    user: User | None = service.authenticate_user(
        email=form.username, password=form.password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not authenticate user",
        )
    expires_delta: timedelta = timedelta(
        minutes=service.config.auth_token_expire_minute
    )
    access_token: str = service.create_access_token(
        data={"sub": user.email}, expires_delta=expires_delta
    )
    redirect_url = request.url_for("view_photos")
    redirect = RedirectResponse(url=redirect_url, status_code=303)
    redirect.set_cookie(
        key="access_token", value=f"Bearer: {access_token}", httponly=True
    )
    csrf_protect.unset_csrf_cookie(redirect)
    return redirect


@router.get(path="/register")
async def registration_form(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    csrf_protect: Annotated[CsrfProtect, Depends()],
):
    """user registration form"""
    if service.admin_exists():
        return RedirectResponse(url=request.url_for("login_form"), status_code=303)
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(
        name="register.html", context={"request": request, "csrf_token": csrf_token}
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@router.post(path="/register")
async def register_user(
    request: Request,
    form_data: Annotated[UserRegistration, Depends(user_registration_form)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    csrf_protect: Annotated[CsrfProtect, Depends()],
):
    csrf_protect.validate_csrf(request)
    if service.admin_exists():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if service.get_user_by_email(form_data.email) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    user_created = service.create_user(
        firstname=form_data.firstname,
        lastname=form_data.lastname,
        email=form_data.email,
        password=form_data.password,
    )
    if not user_created:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not register user",
        )
    redirect_url = request.url_for("login_form")
    response = RedirectResponse(url=redirect_url, status_code=303)
    csrf_protect.unset_csrf_cookie(response=response)
    return response


@router.get(
    path="/upload",
    response_class=HTMLResponse,
    name="upload_form",
    dependencies=[Depends(get_current_user)],
)
async def upload_form(
    request: Request, csrf_protect: Annotated[CsrfProtect, Depends()]
):
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(
        name="upload.html", context={"request": request, "csrf_token": csrf_token}
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@router.post(
    path="/upload",
    dependencies=[Depends(get_current_user)],
)
async def uploads_photo(
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    collection: Annotated[str, Form()],
    request: Request,
    service: Annotated[PhotoService, Depends(dependency=get_photo_service)],
    config: Annotated[Config, Depends(dependency=get_config)],
    csrf_protect: Annotated[CsrfProtect, Depends()],
):
    csrf_protect.validate_csrf(request)
    validator: PhotoValidator = PhotoValidator(file=file, config=config)

    file_data: bytes | None = await validator.validate()

    if file_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="file empty or too large"
        )

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
    response = RedirectResponse(url=f"{redirect_url}?success=true", status_code=303)
    csrf_protect.unset_csrf_cookie(response)
    return response


@router.get(
    path="/photos",
    dependencies=[Depends(get_current_user)],
)
async def view_photos(
    request: Request,
    service: Annotated[PhotoService, Depends(dependency=get_photo_service)],
    csrf_protect: Annotated[CsrfProtect, Depends()],
):
    """send all photos to view"""
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    photos: Sequence[Photo] = service.get_all_photos()

    image_data: list[dict[str, str | int]] = []
    for photo in photos:
        path: str | None = service.build_photo_url(path=photo.thumbnail_path)
        photo
        if path is None:
            image_data.append({"id": photo.id, "path": ""})
        else:
            image_data.append({"id": photo.id, "path": path})

    response = templates.TemplateResponse(
        name="admin.html",
        context={"request": request, "photos": image_data, "csrf_token": csrf_token},
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"request": request, "photos": image_data},
    )


@router.post(
    path="/photos/delete",
    dependencies=[Depends(get_current_user)],
)
async def delete_photos(
    request: Request,
    service: Annotated[PhotoService, Depends(dependency=get_photo_service)],
    payload: DeletePhotoPayload,
    csrf_protect: Annotated[CsrfProtect, Depends()],
):
    """Delete selected photos from image store and metadata from db"""

    csrf_protect.validate_csrf(request)

    photo_ids: list[int] = payload.photo_ids
    if not photo_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No photos selected",
        )

    for photo_id in photo_ids:
        photo: Photo | None = service.get_photo_by_id(id=photo_id)
        if photo is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Photo not found in db",
            )
        try:
            service.delete_photo_from_db(photo=photo)
            service.delete_from_image_store(
                photo_paths=[photo.thumbnail_path, photo.original_path]
            )
        except Exception as e:
            raise Exception(f"Error: {e}")
