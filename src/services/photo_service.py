from typing import Sequence
from sqlalchemy import select, Select
from sqlalchemy.orm import Session


from src.models.schema import Photo
from src.dependencies.config import Config


class PhotoService:
    def __init__(self, db: Session, config: Config) -> None:
        self.db: Session = db
        self.config: Config = config

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

    def get_hero_photo(self) -> str | None:
        """Queries the db for the hero image. Returns the path to the image"""
        query: Select[tuple[str]] = select(Photo.original_path).where(
            Photo.file_name.contains(other="hero")
        )
        return self.db.execute(statement=query).scalar_one_or_none()

    def get_about_image(self) -> Photo | None:
        """Queries the DB for the about image"""
        query: Select[tuple[Photo]] = select(Photo).where(
            Photo.collection.like(other="about_me")
        )
        return self.db.execute(statement=query).scalar_one_or_none()

    def get_unique_collections(self) -> list[str]:
        """Queries db for all of the unique collection names"""
        query: Select[tuple[str]] = select(Photo.collection).distinct()
        results = self.db.execute(statement=query).scalars().all()
        return list(results)
