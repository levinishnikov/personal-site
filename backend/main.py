from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from pathlib import Path
from typing import List
from datetime import date
import os
import models
import database
import schemas
import sync

from sqlalchemy import text, or_

models.Base.metadata.create_all(bind=database.engine)

# Add new columns to existing tables if they don't exist yet
with database.engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE posts ADD COLUMN IF NOT EXISTS publish_date DATE"
    ))
    conn.commit()

app = FastAPI(title="Daniel Levi — Personal Site API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Weekly sync scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(sync.sync_notion_to_db, "interval", weeks=1, id="notion_sync")
scheduler.start()


@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()


# ── Posts ──────────────────────────────────────────────────────────────────

def published_filter():
    return or_(models.Post.publish_date == None, models.Post.publish_date <= date.today())


@app.get("/api/posts", response_model=List[schemas.Post])
def list_posts(db: Session = Depends(database.get_db)):
    return (db.query(models.Post)
              .filter(published_filter())
              .order_by(models.Post.year.desc())
              .all())


@app.get("/api/posts/{slug}", response_model=schemas.Post)
def get_post(slug: str, db: Session = Depends(database.get_db)):
    post = (db.query(models.Post)
              .filter(models.Post.slug == slug, published_filter())
              .first())
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.post("/api/posts", response_model=schemas.Post, status_code=201)
def create_post(post: schemas.PostCreate, db: Session = Depends(database.get_db)):
    if db.query(models.Post).filter(models.Post.slug == post.slug).first():
        raise HTTPException(status_code=409, detail="Slug already exists")
    db_post = models.Post(**post.model_dump())
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


@app.put("/api/posts/{slug}", response_model=schemas.Post)
def update_post(slug: str, post: schemas.PostUpdate, db: Session = Depends(database.get_db)):
    db_post = db.query(models.Post).filter(models.Post.slug == slug).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    for field, value in post.model_dump(exclude_unset=True).items():
        setattr(db_post, field, value)
    db.commit()
    db.refresh(db_post)
    return db_post


@app.delete("/api/posts/{slug}", status_code=204)
def delete_post(slug: str, db: Session = Depends(database.get_db)):
    db_post = db.query(models.Post).filter(models.Post.slug == slug).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(db_post)
    db.commit()


# ── Sync ───────────────────────────────────────────────────────────────────

@app.post("/api/sync")
def trigger_sync(x_sync_secret: str = Header(default="")):
    secret = os.getenv("SYNC_SECRET", "")
    if secret and x_sync_secret != secret:
        raise HTTPException(status_code=401, detail="Invalid sync secret")
    try:
        result = sync.sync_notion_to_db()
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# Static files — must be mounted last so API routes take priority
static_dir = Path(__file__).parent.parent
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
