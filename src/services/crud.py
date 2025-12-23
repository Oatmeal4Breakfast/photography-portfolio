from typing import Sequence
from sqlalchemy import select, Select
from sqlalchemy.orm import Session
from src.models.models import Photo


def get_photo_by_hash(hash: str, db: Session) -> Photo | None:
    """queries the db for photo by hash"""
    if hash is None:
        raise ValueError("hash cannot be empty.")

    query: Select[tuple[Photo]] = select(Photo).where(Photo.hash == hash)
    return db.execute(statement=query).scalars().one_or_none()


def get_photo_by_file_name(file_name: str, db: Session) -> Photo | None:
    """queries the db for photo by file_name"""
    if file_name is None:
        raise ValueError("file_name cannot be empty.")

    original_file_name: str = file_name.split(sep="_")[0]
    query: Select[tuple[Photo]] = select(Photo).where(
        Photo.file_name.contains(other=original_file_name)
    )
    return db.execute(statement=query).scalars().one_or_none()


def get_photos_by_collection(collection_name: str, db: Session) -> Sequence[Photo]:
    if collection_name is None:
        raise ValueError("collection_name cannot be empty")

    query: Select[tuple[Photo]] = select(Photo).where(
        Photo.collection.like(other=collection_name)
    )
    return db.execute(statement=query).scalars().all()


def get_hero_photo(db: Session) -> str | None:
    """queries the db for the hero image. Returns path to image"""
    query: Select[tuple[str]] = select(Photo.original_path).where(
        Photo.file_name.contains(other="hero")
    )
    return db.execute(statement=query).scalar_one_or_none()


def add_photo(photo: Photo, db: Session) -> None:
    """add photo to the db"""
    db.add(instance=photo)
    db.commit()


def delete_photo_from_db(photo: Photo, db: Session) -> None:
    """deletes a photo"""
    db.delete(instance=photo)
    db.commit()
