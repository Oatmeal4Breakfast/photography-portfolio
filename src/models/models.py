from pydantic import BaseModel, Field, EmailStr
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


class UserRegistration(BaseModel):
    firstname: str = Field(..., min_length=2, max_length=15)
    lastname: str = Field(..., min_length=2, max_length=20)
    email: EmailStr = Field(..., max_length=50)
    password: str = Field(..., min_length=12, max_length=128)


class UserInDB(User):
    hashed_password: str
