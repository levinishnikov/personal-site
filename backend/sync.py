import os
import re
from datetime import date
from notion_client import Client
from sqlalchemy.orm import Session
import models
from database import SessionLocal

notion = Client(auth=os.getenv("NOTION_API_KEY", ""))
DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")


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
        if ann.get("bold"):
            text = f"<strong>{text}</strong>"
        if ann.get("italic"):
            text = f"<em>{text}</em>"
        if ann.get("code"):
            text = f"<code>{text}</code>"
        if href:
            text = f'<a href="{href}" target="_blank" rel="noopener noreferrer">{text}</a>'
        html += text
    return html


def blocks_to_html(blocks: list) -> str:
    html = ""
    i = 0
    while i < len(blocks):
        block = blocks[i]
        btype = block["type"]
        content = block.get(btype, {})
        rich = content.get("rich_text", [])

        if btype == "paragraph":
            inner = rich_text_to_html(rich)
            if inner:
                html += f"<p>{inner}</p>\n"
        elif btype in ("heading_1", "heading_2"):
            html += f"<h2>{rich_text_to_html(rich)}</h2>\n"
        elif btype == "heading_3":
            html += f"<h3>{rich_text_to_html(rich)}</h3>\n"
        elif btype == "bulleted_list_item":
            items = []
            while i < len(blocks) and blocks[i]["type"] == "bulleted_list_item":
                r = blocks[i]["bulleted_list_item"].get("rich_text", [])
                items.append(f"<li>{rich_text_to_html(r)}</li>")
                i += 1
            html += f"<ul>{''.join(items)}</ul>\n"
            continue
        elif btype == "numbered_list_item":
            items = []
            while i < len(blocks) and blocks[i]["type"] == "numbered_list_item":
                r = blocks[i]["numbered_list_item"].get("rich_text", [])
                items.append(f"<li>{rich_text_to_html(r)}</li>")
                i += 1
            html += f"<ol>{''.join(items)}</ol>\n"
            continue
        elif btype == "code":
            code = "".join(s.get("plain_text", "") for s in rich)
            html += f"<pre><code>{code}</code></pre>\n"
        elif btype == "quote":
            html += f"<blockquote>{rich_text_to_html(rich)}</blockquote>\n"
        elif btype == "divider":
            html += "<hr>\n"

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
            # Пропускаем если Published не отмечен
            if not page["properties"].get("Published", {}).get("checkbox", False):
                continue
            props = page["properties"]

            # Title — поддерживает "Name", "Title", "title"
            title_prop = props.get("Name") or props.get("Title") or props.get("title") or {}
            title = "".join(t.get("plain_text", "") for t in title_prop.get("title", [])).strip()
            if not title:
                continue

            # Slug — из свойства или из заголовка
            slug_list = props.get("Slug", {}).get("rich_text", [])
            slug = "".join(t.get("plain_text", "") for t in slug_list).strip() or slugify(title)

            # Year — из свойства или из даты создания страницы
            year = props.get("Year", {}).get("number") or int(page["created_time"][:4])

            # Publish date — из свойства "Publish Date"
            publish_date = None
            pd_start = props.get("Publish Date", {}).get("date") or {}
            if pd_start.get("start"):
                publish_date = date.fromisoformat(pd_start["start"][:10])

            # Body — конвертируем блоки Notion в HTML
            blocks = notion.blocks.children.list(block_id=page["id"]).get("results", [])
            body = blocks_to_html(blocks)

            # Upsert
            existing = db.query(models.Post).filter(models.Post.slug == slug).first()
            if existing:
                existing.title = title
                existing.body = body
                existing.year = year
                existing.publish_date = publish_date
            else:
                db.add(models.Post(
                    slug=slug, title=title, body=body,
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
