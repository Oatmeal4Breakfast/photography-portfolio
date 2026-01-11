from enum import StrEnum
from typing import Sequence
from io import BytesIO
from pathlib import Path
from PIL import Image
from sqlalchemy import select, Select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.dependencies.config import Config, EnvType

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
    def __init__(self, db: Session, config: Config) -> None:
        self.db: Session = db
        self.config: Config = config

    
