from typing import List
from sqlalchemy import ForeignKey
from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, MappedAsDataclass
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from datetime import datetime


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class Photo(Base):
    __tablename__ = "photo"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=True)
    file_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    original_path: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    thumbnail_path: Mapped[str] = mapped_column(
        String(300), nullable=False, unique=True
    )
    collection: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)


class User(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    comments: Mapped[List["Comment"]] = relationship(back_populates="user", init=False)


class Comment(Base):
    __tablename__ = "comment"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[datetime] = mapped_column(comment="Time the comment was made")

    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))
    user: Mapped["User"] = relationship(back_populates="comments")
