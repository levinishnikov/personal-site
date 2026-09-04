from sqlalchemy import Column, Integer, String, Text, DateTime, Date
from datetime import datetime, timezone
from database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False, default="")
    # Site-relative path under /static, filled by sync from the Notion `Cover`
    # property. Notion's own file URLs expire about an hour after they are
    # handed out, so nothing stored here ever points back at Notion.
    cover_url = Column(String, nullable=True)
    year = Column(Integer, nullable=False)
    publish_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
