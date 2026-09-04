import hashlib
import os
import re
import urllib.request
from datetime import date
from pathlib import Path
from notion_client import Client
from sqlalchemy.orm import Session
import models
from database import SessionLocal

notion = Client(auth=os.getenv("NOTION_API_KEY", ""))
DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

# Notion hands out presigned file URLs that die after roughly an hour, so every
# picture is copied into our own static dir at sync time and served from there.
# The container filesystem is ephemeral, which is fine: a sync runs on boot, so
# a redeploy refills this directory before anyone can ask for an image.
IMAGE_DIR = Path(__file__).parent.parent / "static" / "post-images"
IMAGE_URL_PREFIX = "/post-images"
IMAGE_EXT = {
    "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
    "image/webp": ".webp", "image/gif": ".gif", "image/avif": ".avif",
}


def cache_image(url: str, slug: str) -> str:
    """Download one Notion image into /static/post-images. Returns its site path.

    Named by content hash, so an unchanged picture is downloaded once and a
    replaced one never collides with its predecessor. Returns "" on any
    failure — a missing picture must never cost us the post's text.
    """
    if not url:
        return ""
    try:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "llmceo-sync"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            ctype = (resp.headers.get("content-type") or "").split(";")[0].strip()
        ext = IMAGE_EXT.get(ctype, ".jpg")
        name = "{}-{}{}".format(slug or "post", hashlib.sha1(data).hexdigest()[:12], ext)
        path = IMAGE_DIR / name
        if not path.exists():
            path.write_bytes(data)
        return "{}/{}".format(IMAGE_URL_PREFIX, name)
    except Exception:
        return ""


def cover_from_props(props: dict, slug: str) -> str:
    """The row's `Cover` property -> a local image path (or "")."""
    files = (props.get("Cover") or {}).get("files") or []
    if not files:
        return ""
    first = files[0]
    url = (first.get("file") or first.get("external") or {}).get("url", "")
    return cache_image(url, slug)


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


def rich_text_to_html(rich_text: list) -> str:
    html = ""
    for seg in rich_text:
        text = seg.get("plain_text", "")
        if not text:
            continue
        ann = seg.get("annotations", {})
        href = seg.get("href")

        if ann.get("code"):
            text = f"<code>{text}</code>"
        else:
            if ann.get("bold"):
                text = f"<strong>{text}</strong>"
            if ann.get("italic"):
                text = f"<em>{text}</em>"
            if ann.get("strikethrough"):
                text = f"<s>{text}</s>"
            if ann.get("underline"):
                text = f"<u>{text}</u>"

        color = ann.get("color", "default")
        if color and color != "default" and not color.endswith("_background"):
            text = f'<span class="color-{color}">{text}</span>'

        if href:
            text = f'<a href="{href}" target="_blank" rel="noopener noreferrer">{text}</a>'

        html += text
    return html


def get_children(block_id: str) -> list:
    try:
        return notion.blocks.children.list(block_id=block_id).get("results", [])
    except Exception:
        return []


def blocks_to_html(blocks: list, depth: int = 0, slug: str = "") -> str:
    html = ""
    i = 0
    while i < len(blocks):
        block = blocks[i]
        btype = block["type"]
        content = block.get(btype, {})
        rich = content.get("rich_text", [])
        has_children = block.get("has_children", False)

        if btype == "paragraph":
            inner = rich_text_to_html(rich)
            html += f"<p>{inner}</p>\n" if inner else "<br>\n"

        elif btype == "heading_1":
            html += f"<h2>{rich_text_to_html(rich)}</h2>\n"
        elif btype == "heading_2":
            html += f"<h2>{rich_text_to_html(rich)}</h2>\n"
        elif btype == "heading_3":
            html += f"<h3>{rich_text_to_html(rich)}</h3>\n"

        elif btype == "bulleted_list_item":
            items = []
            while i < len(blocks) and blocks[i]["type"] == "bulleted_list_item":
                r = blocks[i]["bulleted_list_item"].get("rich_text", [])
                item_html = rich_text_to_html(r)
                if blocks[i].get("has_children"):
                    children = get_children(blocks[i]["id"])
                    item_html += blocks_to_html(children, depth + 1, slug)
                items.append(f"<li>{item_html}</li>")
                i += 1
            html += f"<ul>{''.join(items)}</ul>\n"
            continue

        elif btype == "numbered_list_item":
            items = []
            while i < len(blocks) and blocks[i]["type"] == "numbered_list_item":
                r = blocks[i]["numbered_list_item"].get("rich_text", [])
                item_html = rich_text_to_html(r)
                if blocks[i].get("has_children"):
                    children = get_children(blocks[i]["id"])
                    item_html += blocks_to_html(children, depth + 1, slug)
                items.append(f"<li>{item_html}</li>")
                i += 1
            html += f"<ol>{''.join(items)}</ol>\n"
            continue

        elif btype == "to_do":
            checked = "checked" if content.get("checked") else ""
            text = rich_text_to_html(rich)
            html += f'<p class="todo"><label><input type="checkbox" disabled {checked}> {text}</label></p>\n'

        elif btype == "code":
            code = "".join(s.get("plain_text", "") for s in rich)
            lang = content.get("language", "")
            html += f'<pre><code class="language-{lang}">{code}</code></pre>\n'

        elif btype == "quote":
            inner = rich_text_to_html(rich)
            children_html = blocks_to_html(get_children(block["id"]), depth + 1, slug) if has_children else ""
            html += f"<blockquote>{inner}{children_html}</blockquote>\n"

        elif btype == "callout":
            icon_obj = content.get("icon", {})
            icon = icon_obj.get("emoji", "") if icon_obj.get("type") == "emoji" else "💡"
            inner = rich_text_to_html(rich)
            children_html = blocks_to_html(get_children(block["id"]), depth + 1, slug) if has_children else ""
            html += f'<div class="callout"><span class="callout-icon">{icon}</span><div>{inner}{children_html}</div></div>\n'

        elif btype == "toggle":
            inner = rich_text_to_html(rich)
            children_html = blocks_to_html(get_children(block["id"]), depth + 1, slug) if has_children else ""
            html += f"<details><summary>{inner}</summary>{children_html}</details>\n"

        elif btype == "divider":
            html += "<hr>\n"

        elif btype == "image":
            file_obj = content.get("file") or content.get("external") or {}
            url = file_obj.get("url", "")
            caption_html = rich_text_to_html(content.get("caption", []))
            # Copy it locally: a Notion URL rendered straight into the page
            # goes dead about an hour after this sync ran.
            local = cache_image(url, slug)
            if local:
                html += f'<figure><img src="{local}" alt="{caption_html}" loading="lazy"><figcaption>{caption_html}</figcaption></figure>\n'

        elif btype == "table":
            rows = get_children(block["id"])
            html += "<table>\n"
            for j, row in enumerate(rows):
                cells = row.get("table_row", {}).get("cells", [])
                tag = "th" if j == 0 and content.get("has_column_header") else "td"
                html += "<tr>" + "".join(
                    f"<{tag}>{rich_text_to_html(cell)}</{tag}>" for cell in cells
                ) + "</tr>\n"
            html += "</table>\n"

        elif btype == "column_list":
            columns = get_children(block["id"])
            html += '<div class="columns">\n'
            for col in columns:
                col_blocks = get_children(col["id"])
                html += f'<div class="column">{blocks_to_html(col_blocks, depth + 1, slug)}</div>\n'
            html += "</div>\n"

        else:
            plain = "".join(s.get("plain_text", "") for s in rich)
            if plain:
                html += f"<p>{plain}</p>\n"

        i += 1
    return html


def sync_notion_to_db() -> dict:
    if not DATABASE_ID or not os.getenv("NOTION_API_KEY"):
        return {"status": "skipped", "reason": "Notion credentials not set"}

    db: Session = SessionLocal()
    synced = 0
    try:
        response = notion.databases.query(database_id=DATABASE_ID)
        pages = response.get("results", [])

        for page in pages:
            props = page["properties"]

            if not props.get("Published", {}).get("checkbox", False):
                continue

            title_prop = props.get("Name") or props.get("Title") or props.get("title") or {}
            title = "".join(t.get("plain_text", "") for t in title_prop.get("title", [])).strip()
            if not title:
                continue

            slug_list = props.get("Slug", {}).get("rich_text", [])
            slug = "".join(t.get("plain_text", "") for t in slug_list).strip() or slugify(title)

            year = props.get("Year", {}).get("number") or int(page["created_time"][:4])

            publish_date = None
            pd_start = (props.get("Publish Date") or {}).get("date") or {}
            if pd_start.get("start"):
                publish_date = date.fromisoformat(pd_start["start"][:10])

            blocks = notion.blocks.children.list(block_id=page["id"]).get("results", [])
            body = blocks_to_html(blocks, slug=slug)
            cover_url = cover_from_props(props, slug)

            existing = db.query(models.Post).filter(models.Post.slug == slug).first()
            if existing:
                existing.title = title
                existing.body = body
                existing.year = year
                existing.publish_date = publish_date
                # Keep the picture we already have if this run could not fetch
                # one; a transient download failure must not blank the page.
                if cover_url:
                    existing.cover_url = cover_url
            else:
                db.add(models.Post(
                    slug=slug, title=title, body=body, cover_url=cover_url or None,
                    year=year, publish_date=publish_date
                ))
            synced += 1

        db.commit()
        return {"status": "ok", "synced": synced}

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Sync failed: {e}") from e
    finally:
        db.close()
