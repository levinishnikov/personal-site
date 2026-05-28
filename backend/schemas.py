from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional


class PostCreate(BaseModel):
    slug: str
    title: str
    body: str
    year: int
    publish_date: Optional[date] = None


class PostUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    year: Optional[int] = None
    publish_date: Optional[date] = None


class Post(BaseModel):
    id: int
    slug: str
    title: str
    body: str
    year: int
    publish_date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}
