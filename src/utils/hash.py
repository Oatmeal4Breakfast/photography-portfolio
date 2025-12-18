import hashlib
from sqlalchemy.orm import Session
from src.models.models import Photo


def get_hash(file_data: bytes) -> str:
    """Returns the hashed string of the file"""
    return hashlib.sha256(data=file_data).hexdigest()


def photo_hash_exists(hash: str, db: Session) -> bool:
    """
    Returns True if photo found with matching hash
    """
    result: Photo | None = db.query(Photo).filter(Photo.hash == hash).first()
    if result is None:
        return False
    return True


def get_photo_by_hash(hash: str, db: Session) -> Photo | None:
    return db.query(Photo).filter(Photo.hash == hash).first()
