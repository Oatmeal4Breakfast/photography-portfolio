from pydantic import BaseModel
from typing import List
from src.models.schema import UserType


class DeletePhotoPayload(BaseModel):
    photo_ids: List[int]


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class User(BaseModel):
    firstname: str | None = None
    lastname: str | None = None
    email: str | None = None
    user_type: UserType = UserType.USER
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str
