"""SEO / GEO helpers: entity graph, excerpts, sitemap, RSS feed.

All public URLs are absolute against the canonical host so crawlers and
LLM retrievers see consistent, self-describing pages.
"""
import re
import json
import html
from datetime import date, datetime, timezone
from email.utils import format_datetime

BASE = "https://llmceo.com"
IMAGE = f"{BASE}/daniel-levinishnikov.jpg"
FACTUAL_DESCRIPTION = (
    "Head of AI Products at T-Bank, building LLM agents, chatbots and voice "
    "systems for customer support automation."
)


# ── Text helpers ─────────────────────────────────────────────────────────────

def excerpt(body_html: str, limit: int = 155) -> str:
    text = re.sub(r"<[^>]+>", " ", body_html or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def xesc(s: str) -> str:
    return html.escape(s or "", quote=False)


# ── Dates ────────────────────────────────────────────────────────────────────

def iso_date(post) -> str:
    if post.publish_date:
        return post.publish_date.isoformat()
    return f"{post.year}-01-01"


def date_label(post) -> str:
    """Short label for lists: 'May 2026' or just the year."""
    if post.publish_date:
        return post.publish_date.strftime("%b %Y")
    return str(post.year)


def date_full(post) -> str:
    """Long label for the post header: 'May 29, 2026' or just the year."""
    if post.publish_date:
        day = post.publish_date.day
        return post.publish_date.strftime(f"%B {day}, %Y")
    return str(post.year)


def rfc822(post) -> str:
    if post.publish_date:
        dt = datetime(post.publish_date.year, post.publish_date.month,
                      post.publish_date.day, tzinfo=timezone.utc)
    else:
        dt = datetime(post.year, 1, 1, tzinfo=timezone.utc)
    return format_datetime(dt)


def post_view(post) -> dict:
    """Plain dict for templates — keeps date logic out of the markup."""
    return {
        "slug": post.slug,
        "title": post.title,
        "date_label": date_label(post),
        "date_full": date_full(post),
    }


# ── JSON-LD entity graph ──────────────────────────────────────────────────────

def _website_node() -> dict:
    return {
        "@type": "WebSite",
        "@id": f"{BASE}/#website",
        "url": f"{BASE}/",
        "name": "Daniel Levinishnikov",
        "publisher": {"@id": f"{BASE}/#daniel"},
        "inLanguage": "en",
    }


def _person_node() -> dict:
    return {
        "@type": "Person",
        "@id": f"{BASE}/#daniel",
        "name": "Daniel Levinishnikov",
        "url": f"{BASE}/",
        "image": IMAGE,
        "jobTitle": "Head of AI Products",
        "worksFor": {"@type": "Organization", "name": "T-Bank", "url": "https://www.tbank.ru/"},
        "knowsAbout": [
            "AI products", "LLM agents", "Conversational AI", "Chatbots",
            "Voice bots", "Machine learning", "Product management",
        ],
        "description": FACTUAL_DESCRIPTION,
        "sameAs": [
            "https://www.wikidata.org/wiki/Q139973632",
            "https://t.me/llm_ceo1",
            "https://www.linkedin.com/in/levinishnikov",
            "https://github.com/levinishnikov",
        ],
    }


def _breadcrumb_node(items: list) -> dict:
    return {
        "@type": "BreadcrumbList",
        "@id": items[-1][1] + "#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    }


def _serialize(*page_nodes) -> str:
    data = {"@context": "https://schema.org", "@graph": [_website_node(), _person_node(), *page_nodes]}
    return json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")


def home_graph() -> str:
    return _serialize({
        "@type": "ProfilePage",
        "@id": f"{BASE}/#webpage",
        "url": f"{BASE}/",
        "name": "Daniel Levinishnikov — Head of AI Products at T-Bank",
        "isPartOf": {"@id": f"{BASE}/#website"},
        "about": {"@id": f"{BASE}/#daniel"},
        "mainEntity": {"@id": f"{BASE}/#daniel"},
        "primaryImageOfPage": IMAGE,
        "inLanguage": "en",
    })


def posts_graph() -> str:
    return _serialize(
        {
            "@type": "CollectionPage",
            "@id": f"{BASE}/posts.html#webpage",
            "url": f"{BASE}/posts.html",
            "name": "Posts — Daniel Levinishnikov",
            "isPartOf": {"@id": f"{BASE}/#website"},
            "about": {"@id": f"{BASE}/#daniel"},
            "primaryImageOfPage": IMAGE,
            "inLanguage": "en",
        },
        _breadcrumb_node([("Home", f"{BASE}/"), ("Posts", f"{BASE}/posts.html")]),
    )


def post_graph(post) -> str:
    url = f"{BASE}/posts/{post.slug}"
    d = iso_date(post)
    return _serialize(
        {
            "@type": "BlogPosting",
            "@id": f"{url}#post",
            "headline": post.title,
            "datePublished": d,
            "dateModified": d,
            "url": url,
            "mainEntityOfPage": url,
            "author": {"@id": f"{BASE}/#daniel"},
            "publisher": {"@id": f"{BASE}/#daniel"},
            "isPartOf": {"@id": f"{BASE}/#website"},
            "image": IMAGE,
            "inLanguage": "en",
        },
        _breadcrumb_node([
            ("Home", f"{BASE}/"),
            ("Posts", f"{BASE}/posts.html"),
            (post.title, url),
        ]),
    )


# ── sitemap.xml ───────────────────────────────────────────────────────────────

def build_sitemap(posts: list) -> str:
    today = date.today().isoformat()
    urls = [(f"{BASE}/", today), (f"{BASE}/posts.html", today)]
    urls += [(f"{BASE}/posts/{p.slug}", iso_date(p)) for p in posts]
    body = "".join(
        f"<url><loc>{loc}</loc><lastmod>{mod}</lastmod></url>" for loc, mod in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{body}</urlset>"
    )


# ── feed.xml (RSS 2.0) ────────────────────────────────────────────────────────

def build_feed(posts: list) -> str:
    items = []
    for p in posts:
        url = f"{BASE}/posts/{p.slug}"
        items.append(
            "<item>"
            f"<title>{xesc(p.title)}</title>"
            f"<link>{url}</link>"
            f'<guid isPermaLink="true">{url}</guid>'
            f"<pubDate>{rfc822(p)}</pubDate>"
            f"<description>{xesc(excerpt(p.body))}</description>"
            "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        "<title>Daniel Levinishnikov</title>"
        f"<link>{BASE}/</link>"
        "<description>Head of AI Products at T-Bank. Posts on building useful AI.</description>"
        "<language>en</language>"
        f'<atom:link href="{BASE}/feed.xml" rel="self" type="application/rss+xml"/>'
        + "".join(items) +
        "</channel></rss>"
    )


# ── 404 ───────────────────────────────────────────────────────────────────────

def render_404_html() -> str:
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        "<title>Not found — Daniel Levinishnikov</title>"
        "<meta name=\"robots\" content=\"noindex\">"
        "<link rel=\"icon\" href=\"/favicon.svg\" type=\"image/svg+xml\">"
        "<link rel=\"stylesheet\" href=\"/styles.css\"></head>"
        "<body><main class=\"post-main\"><div style=\"padding:140px 0;text-align:center\">"
        "<h1 style=\"font-size:64px;letter-spacing:-0.04em\">404</h1>"
        "<p style=\"color:var(--muted);margin:12px 0 24px\">This page slipped past the AI.</p>"
        "<a href=\"/\" class=\"all-posts-link\">← Back home</a>"
        "</div></main></body></html>"
    )
