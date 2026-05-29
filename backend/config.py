"""Site configuration — every personal detail lives here as an env var.

Fork this repo, copy .env.example to .env, fill in your values, and you're done.
Templates and SEO helpers read from this module — you never need to touch them.
"""
import os


# ── Identity ──────────────────────────────────────────────────────────────────

OWNER_NAME       = os.getenv("OWNER_NAME",        "Your Name")
OWNER_NAME_FIRST = os.getenv("OWNER_NAME_FIRST",  "Your")
OWNER_NAME_LAST  = os.getenv("OWNER_NAME_LAST",   "Name")
OWNER_TITLE      = os.getenv("OWNER_TITLE",       "Your Title")
OWNER_EMPLOYER   = os.getenv("OWNER_EMPLOYER",    "Your Company")
OWNER_EMPLOYER_URL = os.getenv("OWNER_EMPLOYER_URL", "")
OWNER_DESCRIPTION  = os.getenv(
    "OWNER_DESCRIPTION",
    "Personal website and blog.",
)
OWNER_KNOWS_ABOUT = [
    s.strip()
    for s in os.getenv("OWNER_KNOWS_ABOUT", "").split(",")
    if s.strip()
]


# ── Site ─────────────────────────────────────────────────────────────────────

SITE_DOMAIN = os.getenv("SITE_DOMAIN", "https://example.com").rstrip("/")
AVATAR_FILE = os.getenv("AVATAR_FILE", "avatar.jpg")


# ── Social profiles ───────────────────────────────────────────────────────────
# Store only the username/handle — URLs are assembled in templates and seo.py.

OWNER_TELEGRAM = os.getenv("OWNER_TELEGRAM", "")   # handle, no @
OWNER_LINKEDIN = os.getenv("OWNER_LINKEDIN", "")   # username
OWNER_GITHUB   = os.getenv("OWNER_GITHUB",   "")   # username
OWNER_WIKIDATA = os.getenv("OWNER_WIKIDATA", "")   # Q-id, e.g. Q139973632

# Optional second handle promoted at the bottom of each post ("More takes — …").
# Falls back to OWNER_TELEGRAM; the block is hidden if both are empty.
TAKES_TELEGRAM = os.getenv("TAKES_TELEGRAM", "") or OWNER_TELEGRAM


# ── Page copy ─────────────────────────────────────────────────────────────────

HOME_DESCRIPTION  = os.getenv("HOME_DESCRIPTION",  "Personal website.")
POSTS_DESCRIPTION = os.getenv("POSTS_DESCRIPTION", "Posts.")

HERO_CTA_URL  = os.getenv("HERO_CTA_URL",  "")
HERO_CTA_TEXT = os.getenv("HERO_CTA_TEXT", "Get in touch")


# ── Derived helpers ───────────────────────────────────────────────────────────

def telegram_url() -> str:
    return f"https://t.me/{OWNER_TELEGRAM}" if OWNER_TELEGRAM else ""

def linkedin_url() -> str:
    return f"https://www.linkedin.com/in/{OWNER_LINKEDIN}" if OWNER_LINKEDIN else ""

def github_url() -> str:
    return f"https://github.com/{OWNER_GITHUB}" if OWNER_GITHUB else ""

def takes_url() -> str:
    return f"https://t.me/{TAKES_TELEGRAM}" if TAKES_TELEGRAM else ""

def wikidata_url() -> str:
    return f"https://www.wikidata.org/wiki/{OWNER_WIKIDATA}" if OWNER_WIKIDATA else ""

def same_as() -> list[str]:
    return [u for u in [wikidata_url(), telegram_url(), linkedin_url(), github_url()] if u]

def avatar_url() -> str:
    return f"{SITE_DOMAIN}/{AVATAR_FILE}"
