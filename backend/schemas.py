from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PostCreate(BaseModel):
    slug: str
    title: str
    body: str
    year: int


class PostUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    year: Optional[int] = None


class Post(BaseModel):
    id: int
    slug: str
    title: str
    body: str
    year: int
    created_at: datetime

    model_config = {"from_attributes": True}
