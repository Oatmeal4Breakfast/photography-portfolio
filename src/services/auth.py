import jwt
from pwdlib import PasswordHash

password_hash: PasswordHash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """check to see if password entered matches the hash"""
    return password_hash.verify(password=plain_password, hash=hashed_password)


def get_password_hash(password: str) -> str:
    """generate a hashed password"""
    return password_hash.hash(password=password)


def authenticate_user(db: Session, username: str, password: str) -> User | bool:
    """authenticates the user against the db"""
