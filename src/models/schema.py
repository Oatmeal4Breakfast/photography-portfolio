from typing import List
from sqlalchemy import String, Text, ForeignKey, Enum
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)
from datetime import datetime
from enum import StrEnum


class UserType(StrEnum):
    USER = "user"
    ADMIN = "admin"


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class Photo(Base):
    __tablename__ = "photo"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    title: Mapped[str] = mapped_column(String(length=50), nullable=False)
    hash: Mapped[str] = mapped_column(String(length=64), nullable=False, unique=True)
    # description: Mapped[str] = mapped_column(String(length=300), nullable=True)
    file_name: Mapped[str] = mapped_column(
        String(length=50), nullable=False, unique=True
    )
    original_path: Mapped[str] = mapped_column(
        String(length=300), nullable=False, unique=True
    )
    thumbnail_path: Mapped[str] = mapped_column(
        String(length=300), nullable=False, unique=True
    )
    collection: Mapped[str] = mapped_column(
        String(length=100), nullable=False, unique=True
    )


class User(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(length=30))
    email: Mapped[str] = mapped_column(String(length=50), unique=True, nullable=False)
    comments: Mapped[List["Comment"]] = relationship(back_populates="user", init=False)
    hashed_password: Mapped[str] = mapped_column(String(), nullable=False)
    user_type: Mapped[UserType] = mapped_column(Enum(enums=UserType), nullable=False)


class Comment(Base):
    __tablename__ = "comment"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[datetime] = mapped_column(comment="Time the comment was made")

    user_id: Mapped[int] = mapped_column(ForeignKey(column="user_account.id"))
    user: Mapped["User"] = relationship(back_populates="comments")
