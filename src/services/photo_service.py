from sqlalchemy.exc import IntegrityError
from typing import Sequence
from io import BytesIO
from pathlib import Path
from PIL import Image
from sqlalchemy import select, Select
from sqlalchemy.orm import Session
from fastapi import UploadFile

import hashlib
import uuid

from src.models.schema import Photo
from src.config import Config, EnvType


class PhotoValidator:
    def __init__(self, file: UploadFile, config: Config) -> None:
        self.file: UploadFile = file
        self.valid_types: list[str] = [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/webp",
        ]
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

    async def check_file_size(self) -> bytes | None:
        """checks the file for size"""
        chunks: list[bytes] = []
        total: int = 0
        while True:
            chunk: bytes = await self.file.read(size=(1024 * 1024))
            if not chunk:
                break

            total += len(chunk)
            if total > self.max_size:
                return None

            chunks.append(chunk)

        if total == 0:
            return None

        return b"".join(chunks)

    async def validate(self) -> bytes | None:
        "Composes the other methods to validate the file upload"
        if not self.check_exist() or not self.check_file_type():
            raise ValueError("Unsupported file type")
        file_data: bytes | None = await self.check_file_size()
        return file_data


class PhotoService:
    def __init__(self, db: Session, config: Config) -> None:
        self.db: Session = db
        self.config: Config = config

    def _get_output_path(self, file_name: str, subdir: str) -> str:
        """Returns a string of the output path for the image to store in DB"""
        path: Path = Path("uploads") / subdir / file_name
        if self.config.env_type == EnvType.DEVELOPMENT:
            path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    def get_hash(self, file_data: bytes) -> str:
        """Returns the hashed string of the file"""
        return hashlib.sha256(file_data).hexdigest()

    def sanitize_file(self, file_name: str) -> str:
        """sanitizes the file and returns a unique file name"""
        stem: str = Path(file_name).stem
        sanitized_stem: str = stem.replace(" ", "_")[:50]
        return f"{sanitized_stem}_{uuid.uuid4().hex[:8]}.jpeg"

    def create_thumbnail(self, file: bytes, file_name: str) -> str:
        """Compresses image to thumbnail size (300,300)"""
        size = (300, 300)
        path_to_save = Path(
            self._get_output_path(file_name=file_name, subdir="thumbnail")
        )

        try:
            with Image.open(fp=BytesIO(initial_bytes=file)) as img:
                img.thumbnail(size=size, resample=Image.Resampling.LANCZOS)
                img.save(path_to_save, format="JPEG")
                return str(path_to_save)
        except IOError:
            raise

    def create_original(self, file: bytes, file_name: str) -> str:
        """Returns path to save file of the original size"""
        path_to_save: Path = Path(
            self._get_output_path(file_name=file_name, subdir="original")
        )
        try:
            with Image.open(fp=BytesIO(initial_bytes=file)) as img:
                img.save(path_to_save, format="JPEG")
                return str(path_to_save)
        except IOError:
            raise

    def delete_from_image_store(self, photo_paths: list[str | Path]) -> None:
        """deletes the path to the image form the file store"""
        for path in photo_paths:
            item: Path = Path(path)
            if item.is_file():
                item.unlink(missing_ok=True)

    def photo_hash_exists(self, hash: str) -> bool:
        """checks the db for an existing photo of the same hash"""
        query: Select[tuple[Photo]] = select(Photo).where(Photo.hash == hash)
        result: Photo | None = self.db.execute(statement=query).scalars().one_or_none()
        return result is not None

    def get_photo_by_hash(self, hash: str) -> Photo | None:
        """Queries the db for the photo by hash"""
        query: Select[tuple[Photo]] = select(Photo).where(Photo.hash == hash)
        return self.db.execute(statement=query).scalars().one_or_none()

    def get_photo_by_file_name(self, file_name: str) -> Photo | None:
        """Queries the db for photo by file_name"""
        original_file_name: str = file_name.split(sep="_")[0]
        query: Select[tuple[Photo]] = select(Photo).where(
            Photo.file_name.contains(other=original_file_name)
        )
        return self.db.execute(statement=query).scalars().one_or_none()

    def get_photo_by_id(self, id: int) -> Photo | None:
        """Queries the db for the photo by id"""
        query: Select[tuple[Photo]] = select(Photo).where(Photo.id == id)
        return self.db.execute(statement=query).scalar_one_or_none()

    def get_photos_by_collection(self, collection_name: str) -> Sequence[Photo]:
        """Queries the DB by collection name"""
        query: Select[tuple[Photo]] = select(Photo).where(
            Photo.collection.like(other=collection_name)
        )
        return self.db.execute(statement=query).scalars().all()

    def get_all_photos(self) -> Sequence[Photo]:
        """Queries the db for all photos in the db"""
        query: Select[tuple[Photo]] = select(Photo)
        return self.db.execute(statement=query).scalars().all()

    def get_hero_photo(self) -> str | None:
        """Queries the db for the hero image. Returns the path to the image"""
        query: Select[tuple[str]] = select(Photo.original_path).where(
            Photo.file_name.contains(other="hero")
        )
        return self.db.execute(statement=query).scalar_one_or_none()

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

    def upload_photo(
        self, title: str, file_name: str, file_data: bytes, collection: str
    ) -> Photo | None:
        """Compose method to upload the image to the image store and store the image metadata to db"""
        file_hash: str = self.get_hash(file_data)
        file_name: str = self.sanitize_file(file_name=file_name)

        if self.photo_hash_exists(hash=file_hash):
            raise ValueError("Duplicate Photo")

        try:
            thumbnail_path: str = self.create_thumbnail(
                file=file_data, file_name=file_name
            )
            original_path: str = self.create_original(
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
