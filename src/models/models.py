from pydantic import BaseModel
from typing import List


class DeletePhotoPayload(BaseModel):
    photo_ids: List[int]


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hasshed_password: str
