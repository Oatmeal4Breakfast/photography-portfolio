import hashlib
from sqlalchemy import Select, select
from sqlalchemy.orm import Session
from src.models.schema import Photo


def get_hash(file_data: bytes) -> str:
    """Returns the hashed string of the file"""
    return hashlib.sha256(data=file_data).hexdigest()


def photo_hash_exists(hash: str, db: Session) -> bool:
    """
    Returns True if photo found with matching hash
    """
    query: Select[tuple[str]] = select(Photo.file_name).where(Photo.hash == hash)
    if db.execute(statement=query).scalars().one_or_none() is None:
        return False
    return True
