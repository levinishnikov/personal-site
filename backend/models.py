from sqlalchemy import Column, Integer, String, Text, DateTime, Date
from datetime import datetime, timezone
from database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False, default="")
    year = Column(Integer, nullable=False)
    publish_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
