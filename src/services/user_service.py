import jwt
from sqlalchemy.orm import Session
from sqlalchemy import select, Select
from sqlalchemy.exc import IntegrityError
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone

from src.dependencies.config import Config
from src.models.schema import User, UserType


password_hash: PasswordHash = PasswordHash.recommended()


class CredentialsException(Exception):
    pass


class AuthService:
    def __init__(self, db: Session, config: Config) -> None:
        self.db = db
        self.config = config
        self.password_hash: PasswordHash = password_hash

    def admin_exists(self) -> bool:
        """checks db for existing admin user"""
        query: Select[tuple[User]] = select(User).where(
            User.user_type == UserType.ADMIN
        )
        results: User | None = self.db.execute(statement=query).scalars().one_or_none()
        if results is None:
            return False
        return True

    def create_user(
        self, firstname: str, lastname: str, email: str, password: str
    ) -> bool:
        """create user in db"""
        hashed_password = self.get_password_hash(password)
        user = User(
            firstname=firstname,
            lastname=lastname,
            email=email,
            hashed_password=hashed_password,
            user_type=UserType.ADMIN,
            is_enabled=True,
        )
        try:
            self.db.add(instance=user)
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            raise

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

    def authenticate_user(self, email: str, password: str) -> User | None:
        """authenticates the user against the db"""
        user = self.get_user_by_email(email=email)
        print(user)
        if not user:
            return None
        if not self.verify_password(
            plain_password=password, hashed_password=user.hashed_password
        ):
            return None
        return user

    def create_access_token(
        self, data: dict, expires_delta: timedelta | None = None
    ) -> str:
        """create access token for authentication"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt: str = jwt.encode(
            payload=to_encode,
            key=self.config.secret_key,
            algorithm=self.config.algorithm,
        )
        return encoded_jwt

    def verify_access_token(self, token: str) -> User | None:
        """reads in the JWT token and attempts to return the user"""
        try:
            payload = jwt.decode(
                jwt=token,
                key=self.config.secret_key,
                algorithms=[self.config.algorithm],
            )
            email: str | None = payload.get("sub")
            if email is None:
                return None
            return self.get_user_by_email(email)
        except jwt.PyJWTError:
            return None
