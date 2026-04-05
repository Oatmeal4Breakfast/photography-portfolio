from enum import StrEnum
from typing import Sequence, Protocol
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps
from sqlalchemy import select, Select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import uuid
import hashlib

from src.dependencies.config import Config, EnvType
from src.dependencies.logging import get_logger
from src.dependencies.store import ImageStore, ImagePaths
from src.models.schema import Photo


class InvalidImageType(Exception):
    pass


class ImageTooLarge(Exception):
    pass


class ImageDoesNotExist(Exception):
    pass


class ImageReadError(Exception):
    pass


class ImageUpload(Protocol):
    filename: str
    content_type: str | None
    data: bytes

    async def read(self, size: int = -1) -> bytes: ...
    async def seek(self, offset: int) -> None: ...


class ValidTypes(StrEnum):
    jpeg = "image/jpeg"
    jpg = "image/jpg"
    png = "image/png"
    webp = "image/webp"


class PhotoValidator:
    def __init__(self, file: ImageUpload, config: Config) -> None:
        self.file: ImageUpload = file
        self.valid_types: list[str] = [type.value for type in ValidTypes]
        self.max_size: int = config.max_image_size
        self.logger = get_logger(name=__name__, config=config)

    def check_exist(self) -> bool:
        """check that the file exists"""
        return bool(self.file.filename)

    def check_file_type(self) -> bool:
        """check for valid file type"""
        file_type: str | None = self.file.content_type
        if file_type not in self.valid_types:
            return False
        return True

    async def check_file_size(self) -> bytes:
        """checks the file for size"""
        chunks: list[bytes] = []
        total: int = 0
        while True:
            chunk: bytes = await self.file.read(size=(1024 * 1024))
            if not chunk:
                break

            total += len(chunk)
            if total > self.max_size:
                self.logger.error(
                    f"{self.file.filename} is too large. Must be {self.config.max_image_size}"
                )
                raise ImageTooLarge("Image too large")

            chunks.append(chunk)

        if total == 0:
            self.logger.error(f"{self.file.filename} has no data.")
            raise ImageDoesNotExist("Image has no data")

        self.logger.info(msg=f"{self.file.filename} successfully parsed")
        return b"".join(chunks)

    async def validate(self) -> bytes | None:
        "Composes the other methods to validate the file upload"
        if not self.check_exist() or not self.check_file_type():
            self.logger.error(f"{self.file.filename} is of unsupported type")
            raise ValueError("Unsupported file type")
        file_data: bytes | None = await self.check_file_size()
        return file_data


class AdminService:
    def __init__(self, db: Session, config: Config, store: ImageStore) -> None:
        self.db: Session = db
        self.config: Config = config
        self.store: ImageStore = store
        self.logger = get_logger(name=__name__, config=config)

    def _sanitize_file(self, file_name: str) -> str:
        """sanitizes the file name with a UUID applied"""
        stem: str = Path(file_name).stem
        sanitized_stem: str = stem.replace(" ", "_")[:50]
        self.logger.info(msg=f"{file_name} has been sanitzed...")
        return f"{sanitized_stem}_{uuid.uuid4().hex[:8]}.jpeg"

    def _get_hash(self, file_data: bytes) -> str:
        """Returns the hashed string of the file"""
        return hashlib.sha256(file_data).hexdigest()

    def _get_output_path(self, file_name: str, subdir: str) -> str:
        """Returns a string of the output path for the iamge to store in the DB"""
        path: Path = Path("uploads") / subdir / file_name
        if self.config.env_type == EnvType.DEVELOPMENT:
            path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    def _process_image(self, file: bytes, size: tuple[int, int] | None = None) -> bytes:
        """process the image and return compresses or original file size"""
        bytes_arr = BytesIO()
        with Image.open(fp=BytesIO(initial_bytes=file)) as img:
            img = ImageOps.exif_transpose(img)
            if size is None:
                img.save(bytes_arr, format="JPEG")
                return bytes_arr.getvalue()
            img.thumbnail(size=size, resample=Image.Resampling.LANCZOS)
            img.save(bytes_arr, format="JPEG")
            self.logger.info("file has been proccessed")
            return bytes_arr.getvalue()

    def _add_photo_to_db(self, photo: Photo) -> bool:
        """add photo to database"""
        try:
            self.db.add(instance=photo)
            self.db.commit()
            self.logger.info(msg=f"{photo.file_name} written to databse.")
            return True
        except IntegrityError:
            self.db.rollback()
            self.logger.error(msg=f"{photo.file_name} was not written to the database.")
            raise

    def _delete_photo_from_db(self, photo: Photo) -> None:
        """deletes a photo from the database"""
        try:
            self.db.delete(instance=photo)
            self.logger.info(
                msg=f"{photo.file_name} successfully deleted from databse."
            )
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            self.logger.error(
                msg=f"{photo.file_name} was not deleted from the database."
            )
            raise

    async def _create_thumbnail(self, file: bytes, file_name: str) -> str:
        """creates the thumbnail and returns a path"""
        path_to_save: str = self._get_output_path(file_name, "thumbnail")
        file_data: bytes = self._process_image(file, size=(300, 300))
        results: bool = await self.store.upload_image(file_data, path_to_save)
        if not results:
            self.logger.error(msg=f"{file_name} thumbnail not created")
            raise IOError(f"Could not create thumbnail {path_to_save}")
        self.logger.info(msg=f"{file_name} thumbnail created.")
        return path_to_save

    async def _create_original(self, file: bytes, file_name: str) -> str:
        """create the original and returns a path"""
        path_to_save: str = self._get_output_path(file_name, "original")
        file_data: bytes = self._process_image(file)
        results: bool = await self.store.upload_image(file_data, path_to_save)
        if not results:
            self.logger.error(msg=f"{file_name} original not created")
            raise IOError(f"Could not create original {path_to_save}")
        self.logger.info(msg=f"{file_name} original created.")
        return path_to_save

    def photo_hash_exists(self, hash: str) -> bool:
        """checks the db for an existing photo of the same hash"""
        query: Select[tuple[Photo]] = select(Photo).where(Photo.hash == hash)
        result: Photo | None = self.db.execute(statement=query).scalars().one_or_none()
        return result is not None

    def get_all_photos(self) -> Sequence[Photo]:
        """Queries the db for all photos in the db"""
        query: Select[tuple[Photo]] = select(Photo)
        return self.db.execute(statement=query).scalars().all()

    def get_photo_by_id(self, id: int) -> Photo | None:
        """Queries the db for the photo by id"""
        query: Select[tuple[Photo]] = select(Photo).where(Photo.id == id)
        return self.db.execute(statement=query).scalar_one_or_none()

    async def upload_photo(
        self, title: str, file_name: str | None, file_data: bytes, collection: str
    ) -> Photo | None:
        """
        Upload the image to the Image Store and add to the Photo Object to the Database
        """

        file_hash: str = self._get_hash(file_data)

        if file_name is None:
            self.logger.error("File name must be present.")
            return

        file_name: str = self._sanitize_file(file_name=file_name)

        if self.photo_hash_exists(hash=file_hash):
            self.logger.error(msg=f"Duplicate Photo: photo with hash {file_hash} already exists.")
            raise ValueError(f"Duplicate Photo: photo with hash {file_hash} already exists.")

        try:
            thumbnail_path: str = await self._create_thumbnail(
                file=file_data, file_name=file_name
            )
            original_path: str = await self._create_original(
                file=file_data, file_name=file_name
            )
            new_photo: Photo = Photo(
                title=title,
                hash=file_hash,
                file_name=file_name,
                original_path=original_path,
                thumbnail_path=thumbnail_path,
                collection=collection,
            )
            if self._add_photo_to_db(photo=new_photo):
                return new_photo
        except IOError as e:
            self.logger.error(f"IOError: could not save image: {e}")
            raise IOError(f"Could not save image {e}")
        except Exception as e:
            self.logger.error(f"Error: processing image: {e}")
            raise Exception(f"Error processing image {e}")

    async def delete_photos(self, photos: list[Photo]) -> None:
        """
        Builds ImagePaths and calls the store delete method to then filter make the attempt to remove
        successfully deleted images from the Database
        """
        paths: ImagePaths = []
        for photo in photos:
            paths.append(photo.thumbnail_path)
            paths.append(photo.original_path)

        results: tuple[ImagePaths, ImagePaths] = await self.store.delete_images(
            image_paths=paths
        )

        success, errors = results

        try:
            for photo in photos:
                if photo.original_path in success and photo.thumbnail_path in success:
                    self.db.delete(instance=photo)
            self.db.commit()
            self.logger.info(
                msg=f"Image {photo.file_name} has been successfully deleted"
            )
        except IntegrityError:
            self.logger.error(
                msg=f"Integrety Error: Could not delete image {photo.file_name}"
            )
            self.db.rollback()
            raise
