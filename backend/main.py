from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, or_
from apscheduler.schedulers.background import BackgroundScheduler
from pathlib import Path
from typing import List
from datetime import date, datetime
import os
import logging
import jinja2

import config
import models
import database
import schemas
import sync
import seo

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("bot")

KNOWN_BOTS = {
    "Googlebot":      "Google",
    "Google-Extended":"Google-Extended",
    "Applebot":       "Apple",
    "Bingbot":        "Bing",
    "YandexBot":      "Yandex",
    "PerplexityBot":  "Perplexity",
    "OAI-SearchBot":  "OpenAI-Search",
    "GPTBot":         "GPTBot",
    "ChatGPT-User":   "ChatGPT",
    "ClaudeBot":      "Claude",
    "Claude-User":    "Claude-User",
}

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR      = Path(__file__).parent
STATIC_DIR    = BASE_DIR.parent / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# ── Database ──────────────────────────────────────────────────────────────────

models.Base.metadata.create_all(bind=database.engine)

with database.engine.connect() as conn:
    conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS publish_date DATE"))
    conn.commit()

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title=f"{config.OWNER_NAME} — Personal Site")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Jinja2 ────────────────────────────────────────────────────────────────────
# Custom delimiters keep inline JS/JSON braces untouched.
# Config vars are injected as globals so every template gets them for free.

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
    variable_start_string="[[",  variable_end_string="]]",
    block_start_string="[%",     block_end_string="%]",
    comment_start_string="[#",   comment_end_string="#]",
)
_env.globals.update({
    "owner_name":       config.OWNER_NAME,
    "owner_name_first": config.OWNER_NAME_FIRST,
    "owner_name_last":  config.OWNER_NAME_LAST,
    "owner_title":      config.OWNER_TITLE,
    "owner_employer":   config.OWNER_EMPLOYER,
    "avatar_file":      config.AVATAR_FILE,
    "telegram_url":     config.telegram_url(),
    "linkedin_url":     config.linkedin_url(),
    "github_url":       config.github_url(),
    "owner_telegram":   config.OWNER_TELEGRAM,
    "owner_linkedin":   config.OWNER_LINKEDIN,
    "owner_github":     config.OWNER_GITHUB,
    "takes_telegram":   config.TAKES_TELEGRAM,
    "takes_url":        config.takes_url(),
    "hero_cta_url":     config.HERO_CTA_URL,
    "hero_cta_text":    config.HERO_CTA_TEXT,
    "og_image":         config.avatar_url(),
})

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env = _env

# ── Scheduler ─────────────────────────────────────────────────────────────────

scheduler = BackgroundScheduler()
scheduler.add_job(sync.sync_notion_to_db, "interval", weeks=1, id="notion_sync")
scheduler.start()


@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()


# ── Middleware ────────────────────────────────────────────────────────────────

@app.middleware("http")
async def log_bots(request: Request, call_next):
    ua = request.headers.get("user-agent", "")
    for token, name in KNOWN_BOTS.items():
        if token.lower() in ua.lower():
            ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"[BOT] {ts} | {name} | {request.method} {request.url.path}")
            break
    return await call_next(request)


@app.middleware("http")
async def canonical_host(request: Request, call_next):
    """Redirect www → apex and http → https."""
    host  = request.headers.get("host", "").split(":")[0]
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    apex  = config.SITE_DOMAIN.removeprefix("https://").removeprefix("http://")
    if host.startswith("www."):
        return RedirectResponse(
            str(request.url.replace(scheme="https", netloc=host[4:])), status_code=301
        )
    if host == apex and proto != "https":
        return RedirectResponse(str(request.url.replace(scheme="https")), status_code=301)
    return await call_next(request)


# ── Helpers ───────────────────────────────────────────────────────────────────

def published_filter():
    return or_(models.Post.publish_date == None, models.Post.publish_date <= date.today())


def published_posts(db: Session):
    """Return visible posts, newest first."""
    posts = db.query(models.Post).filter(published_filter()).all()
    return sorted(
        posts,
        key=lambda p: (p.publish_date or date(p.year, 1, 1)),
        reverse=True,
    )


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(database.get_db)):
    posts = published_posts(db)
    return templates.TemplateResponse(request, "index.html", {
        "page_title":       f"{config.OWNER_NAME} — {config.OWNER_TITLE}",
        "page_description": config.HOME_DESCRIPTION,
        "canonical_url":    f"{seo.BASE}/",
        "og_type":          "profile",
        "json_ld":          seo.home_graph(),
        "active_posts":     False,
        "recent_posts":     [seo.post_view(p) for p in posts[:7]],
        "total_posts":      len(posts),
    })


@app.get("/posts.html", response_class=HTMLResponse)
def posts_page(request: Request, db: Session = Depends(database.get_db)):
    posts = published_posts(db)
    return templates.TemplateResponse(request, "posts.html", {
        "page_title":       f"Posts — {config.OWNER_NAME}",
        "page_description": config.POSTS_DESCRIPTION,
        "canonical_url":    f"{seo.BASE}/posts.html",
        "og_type":          "website",
        "json_ld":          seo.posts_graph(),
        "active_posts":     True,
        "posts":            [seo.post_view(p) for p in posts],
        "total_posts":      len(posts),
    })


@app.get("/posts/{slug}", response_class=HTMLResponse)
def post_page(slug: str, request: Request, db: Session = Depends(database.get_db)):
    posts = published_posts(db)
    post  = next((p for p in posts if p.slug == slug), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    related = [seo.post_view(p) for p in posts if p.slug != slug][:3]
    return templates.TemplateResponse(request, "post.html", {
        "page_title":       f"{post.title} — {config.OWNER_NAME}",
        "page_description": seo.excerpt(post.body),
        "canonical_url":    f"{seo.BASE}/posts/{post.slug}",
        "og_type":          "article",
        "json_ld":          seo.post_graph(post),
        "active_posts":     True,
        "post":             seo.post_view(post),
        "body":             post.body,
        "related":          related,
    })


# ── Redirects ─────────────────────────────────────────────────────────────────

@app.get("/index.html")
def redirect_index():
    return RedirectResponse("/", status_code=301)

@app.get("/posts")
def redirect_posts():
    return RedirectResponse("/posts.html", status_code=301)

@app.get("/post.html")
def redirect_legacy_post(slug: str = ""):
    if slug:
        return RedirectResponse(f"/posts/{slug}", status_code=301)
    return RedirectResponse("/posts.html", status_code=301)


# ── Machine-readable ──────────────────────────────────────────────────────────

@app.get("/robots.txt")
def robots():
    return Response(seo.build_robots(), media_type="text/plain")

@app.get("/llms.txt")
def llms():
    return Response(seo.build_llms(), media_type="text/plain")

@app.get("/sitemap.xml")
def sitemap(db: Session = Depends(database.get_db)):
    return Response(seo.build_sitemap(published_posts(db)), media_type="application/xml")

@app.get("/feed.xml")
def feed(db: Session = Depends(database.get_db)):
    return Response(seo.build_feed(published_posts(db)), media_type="application/rss+xml")


# ── JSON API ──────────────────────────────────────────────────────────────────

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

@app.post("/api/sync")
def trigger_sync(x_sync_secret: str = Header(default="")):
    secret = os.getenv("SYNC_SECRET", "")
    if secret and x_sync_secret != secret:
        raise HTTPException(status_code=401, detail="Invalid sync secret")
    try:
        return sync.sync_notion_to_db()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Error handlers ────────────────────────────────────────────────────────────

@app.exception_handler(StarletteHTTPException)
async def not_found_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and not request.url.path.startswith("/api/"):
        return HTMLResponse(seo.render_404_html(), status_code=404)
    return await http_exception_handler(request, exc)


# Static assets — mounted last so app routes take priority
app.mount("/", StaticFiles(directory=str(STATIC_DIR)), name="static")
