from dependencies.store import SignedURLParams
from enum import StrEnum
from typing import Sequence, Protocol
from io import BytesIO
from pathlib import Path
from PIL import Image
from sqlalchemy import select, Select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import uuid
import hashlib

from src.dependencies.config import Config, EnvType
from src.dependencies.store import ImageStore
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
                raise ImageTooLarge("Image too large")

            chunks.append(chunk)

        if total == 0:
            raise ImageDoesNotExist("Image has no data")

        return b"".join(chunks)

    async def validate(self) -> bytes | None:
        "Composes the other methods to validate the file upload"
        if not self.check_exist() or not self.check_file_type():
            raise ValueError("Unsupported file type")
        file_data: bytes | None = await self.check_file_size()
        return file_data


class AdminService:
    def __init__(self, db: Session, config: Config, store: ImageStore) -> None:
        self.db: Session = db
        self.config: Config = config
        self.store: ImageStore = store

    def sanitize_file(self, file_name: str) -> str:
        """sanitizes the file name with a UUID applied"""
        stem: str = Path(file_name).stem
        sanitized_stem: str = stem.replace(" ", "_")[:50]
        return f"{sanitized_stem}_{uuid.uuid4().hex[:8]}.jpeg"

    def get_hash(self, file_data: bytes) -> str:
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
            if size is None:
                img.save(bytes_arr, format="JPEG")
                return bytes_arr.getvalue()
            img.thumbnail(size=size, resample=Image.Resampling.LANCZOS)
            img.save(bytes_arr, format="JPEG")
            return bytes_arr.getvalue()

    def _delete_local(self, photo_paths: list[str | Path]) -> None:
        """helper function to delete local images"""
        for path in photo_paths:
            item: Path = Path(path)
            if item.is_file():
                item.unlink(missing_ok=True)

    def _delete_remote(self, photo_paths: list[str | Path]) -> None:
        """heler function to delete remote images"""
        for path in photo_paths:
            self.store.delete_object(Bucket=self.config.bucket, Key=path)

    def delete_from_image_store(self, photo_paths: list[str | Path]) -> None:
        """deletes the path in to the photo from image store"""
        if self.config.env_type == EnvType.DEVELOPMENT:
            self._delete_local(photo_paths)
        else:
            self._delete_remote(photo_paths)

    def _create_local_thumbnail(self, file: bytes, file_name: str) -> str:
        """save file as thumbnail to local storage"""
        size = (300, 300)
        path_to_image: str = self._get_output_path(file_name, subdir="thumbnail")
        file_data: bytes = self._process_image(file, size)
        try:
            with open(path_to_image, "wb") as fp:
                fp.write(file_data)
            return path_to_image
        except IOError:
            raise

    # TODO: fix this method once you learn the aioboto3 SDK
    async def _create_remote_thumbnail(self, file: bytes, file_name: str) -> str:
        """creates a thumbnail and stores it in the r2 bucket"""
        size = (300, 300)
        file_data: bytes = self._process_image(file, size)
        path_to_image: str = self._get_output_path(
            file_name=file_name, subdir="thumbnail"
        )

        params: SignedURLParams = SignedURLParams(
            Bucket=self.config.bucket,
            Key=path_to_image,
            ContentType=ValidTypes.jpeg.value,
        )
        # ttl measured in seconds
        results = await self.store.upload_image(
            params=params, ttl=3600, file_data=file_data
        )
        if results != 200:
            raise IOError(f"Unable to upload {path_to_image} to remote")
        return path_to_image

    def _create_local_original(self, file: bytes, file_name: str) -> str:
        """returns path to original image"""
        path_to_save = self._get_output_path(file_name, subdir="original")
        file_data = self._process_image(file)
        try:
            with open(path_to_save, "wb") as fp:
                fp.write(file_data)
            return path_to_save
        except IOError:
            raise

    async def _create_remote_original(self, file: bytes, file_name: str) -> str:
        """Uploads image of original size to remote image store"""
        path_to_image: str = self._get_output_path(
            file_name=file_name, subdir="original"
        )
        params: SignedURLParams = SignedURLParams(
            Bucket=self.config.bucket,
            Key=path_to_image,
            ContentType=ValidTypes.jpeg.value,
        )
        results: int = await self.store.upload_image(
            params=params, ttl=3600, file_data=file
        )
        if results != 200:
            raise IOError(f"Unable to upload {path_to_image}")
        return path_to_image

    async def create_thumbnail(self, file: bytes, file_name: str) -> str:
        """creates the thumbnail and returns a path"""
        if self.config.env_type == EnvType.DEVELOPMENT:
            return self._create_local_thumbnail(file, file_name)
        return await self._create_remote_thumbnail(file, file_name)

    async def create_original(self, file: bytes, file_name: str) -> str:
        """create the original and returns a path"""
        if self.config.env_type == EnvType.DEVELOPMENT:
            return self._create_local_original(file, file_name)
        return await self._create_remote_original(file, file_name)

    def photo_hash_exists(self, hash: str) -> bool:
        """checks the db for an existing photo of the same hash"""
        query: Select[tuple[Photo]] = select(Photo).where(Photo.hash == hash)
        result: Photo | None = self.db.execute(statement=query).scalars().one_or_none()
        return result is not None

    def get_all_photos(self) -> Sequence[Photo]:
        """Queries the db for all photos in the db"""
        query: Select[tuple[Photo]] = select(Photo)
        return self.db.execute(statement=query).scalars().all()

    def add_photo_to_db(self, photo: Photo) -> bool:
        """add photo to database"""
        try:
            self.db.add(instance=photo)
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            raise

    def delete_photo_from_db(self, photo: Photo) -> None:
        """deletes a photo from the database"""
        try:
            self.db.delete(instance=photo)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise

    async def upload_photo(
        self, title: str, file_name: str, file_data: bytes, collection: str
    ) -> Photo | None:
        """Compose method to upload the image to the image store and store the image metadata to db"""
        file_hash: str = self.get_hash(file_data)
        file_name: str = self.sanitize_file(file_name=file_name)

        if self.photo_hash_exists(hash=file_hash):
            raise ValueError("Duplicate Photo")

        try:
            thumbnail_path: str = await self.create_thumbnail(
                file=file_data, file_name=file_name
            )
            original_path: str = await self.create_original(
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
            if self.add_photo_to_db(photo=new_photo):
                return new_photo
        except IOError as e:
            raise IOError(f"Could not save image {e}")
        except Exception as e:
            raise Exception(f"Error processing image {e}")
