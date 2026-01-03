from datetime import datetime, timedelta, timezone
import jwt
from sqlalchemy.orm import Session
from sqlalchemy import select, Select
from pwdlib import PasswordHash


from src.config import Config
from models.schema import User


password_hash: PasswordHash = PasswordHash.recommended()


class CredentialsException(Exception):
    pass


class AuthService:
    def __init__(self, db: Session, config: Config) -> None:
        self.db = db
        self.config = config
        self.password_hash: PasswordHash = password_hash

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """check to see if password entered matches the hash"""
        return self.password_hash.verify(password=plain_password, hash=hashed_password)

    def get_password_hash(self, password: str) -> str:
        """generate a hashed password"""
        return self.password_hash.hash(password=password)

    def get_user_by_email(self, email: str) -> User | None:
        """queries the db for a user by email"""
        query: Select[tuple[User]] = select(User).where(User.email == email)
        return self.db.execute(statement=query).scalars().one_or_none()

    def authenticate_user(self, email: str, password: str) -> User | bool:
        """authenticates the user against the db"""
        user = self.get_user_by_email(email=email)
        if not user:
            return False
        if not self.verify_password(
            plain_password=password, hashed_password=user.hashed_password
        ):
            return False
        return user

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None):
        """create access token for authentication"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            payload=to_encode, key=self.config.key, algorithm=self.config.algorithm
        )
        return encoded_jwt
