# personal-site

A minimal, fast personal website with a blog — optimised for LLMs and search engines (GEO/SEO).  
Built with FastAPI + PostgreSQL + Notion sync. Deploys to Railway in minutes.

**Live example:** [llmceo.com](https://llmceo.com) — Daniel Levinishnikov, Head of AI Products at T-Bank.

---

## Features

- **Server-side rendering** — full HTML on first load; crawlers and LLM retrievers see all content
- **Notion CMS** — write posts in Notion, they sync automatically every week (or on demand)
- **JSON-LD entity graph** — Person + WebSite + Article schema on every page
- **Bot-friendly** — robots.txt with explicit AI crawler permissions, llms.txt, dynamic sitemap
- **Liquid glass UI** — Apple-style design with backdrop-filter and specular highlights
- **Bot logging** — every crawler visit appears in deploy logs with `[BOT]` prefix
- **RSS feed** — `/feed.xml` out of the box
- **Zero-JS content** — critical text never depends on JavaScript

---

## Quick start

### 1. Fork & clone

```bash
git clone https://github.com/YOUR_USERNAME/personal-site
cd personal-site
```

### 2. Make it yours

Your **public identity** (name, title, links, descriptions) lives in one committed file:

```
backend/site.env
```

Edit it — that's the only file you need to touch to rebrand the whole site.

Your **secrets** (database URL, Notion token, sync secret) go in `backend/.env` for
local dev, or in Railway variables for production. Never commit them:

```bash
cp .env.example backend/.env   # then fill in your secrets
```

Precedence: real environment variables (Railway) > `backend/.env` > `backend/site.env` > defaults.

### 3. Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

### 4. Customise content

The env vars cover your name, links, and job title.  
For the bio, career path, and other page copy — edit the templates directly:

| What | File |
|---|---|
| Homepage bio & career | `backend/templates/index.html` |
| Avatar photo | Replace `static/avatar.jpg` |
| Favicon | Replace `static/favicon.svg` |
| Styles | `static/styles.css` |

### 5. Deploy to Railway

1. Push your fork to GitHub
2. Create a new Railway project → **Deploy from GitHub repo**
3. Add a **PostgreSQL** service to the project
4. Set all env vars from `.env.example` in Railway → Variables
5. Railway auto-deploys on every push

---

## Environment variables

### Required

| Variable | Example |
|---|---|
| `DATABASE_URL` | `postgresql://user:pass@host/db` |
| `SITE_DOMAIN` | `https://yoursite.com` |
| `OWNER_NAME` | `Jane Smith` |
| `OWNER_NAME_FIRST` | `Jane` |
| `OWNER_NAME_LAST` | `Smith` |
| `OWNER_TITLE` | `Head of Product` |

### Optional but recommended

| Variable | Description |
|---|---|
| `OWNER_EMPLOYER` | Your company name |
| `OWNER_EMPLOYER_URL` | Company website URL |
| `OWNER_DESCRIPTION` | One-sentence bio (used in JSON-LD) |
| `OWNER_TELEGRAM` | Telegram handle (without @) |
| `OWNER_LINKEDIN` | LinkedIn username |
| `OWNER_GITHUB` | GitHub username |
| `OWNER_WIKIDATA` | Wikidata Q-id, e.g. `Q12345678` |
| `OWNER_KNOWS_ABOUT` | Comma-separated expertise list |
| `AVATAR_FILE` | Filename in `static/` (default: `avatar.jpg`) |
| `HERO_CTA_URL` | Hero section CTA button URL |
| `HERO_CTA_TEXT` | Hero section CTA button label |
| `HOME_DESCRIPTION` | Homepage meta description |
| `POSTS_DESCRIPTION` | Posts page meta description |

### Notion sync

| Variable | Description |
|---|---|
| `NOTION_TOKEN` | Notion integration token |
| `NOTION_DATABASE_ID` | ID of the Notion database with posts |
| `SYNC_SECRET` | Secret for `POST /api/sync` webhook (optional) |

---

## Notion database schema

Your Notion database needs these properties:

| Property | Type | Notes |
|---|---|---|
| `Name` | Title | Post title |
| `Slug` | Text | URL path, e.g. `my-first-post` |
| `Year` | Number | Publication year |
| `Publish Date` | Date | Leave empty = published immediately |
| `Status` | Select | Only `Published` rows are synced |

---

## GEO / SEO setup

For your site to appear in LLM answers and search results:

1. **Google Search Console** → verify domain → submit sitemap `https://yoursite.com/sitemap.xml`
2. **Bing Webmaster Tools** → download `BingSiteAuth.xml` → place in `static/` → submit sitemap
3. **Yandex Webmaster** → download verification HTML → place in `static/` → submit sitemap
4. **Wikidata** → create a Person item → add your Q-id to `OWNER_WIKIDATA` env var
5. **Cross-link** → add your site URL to GitHub, LinkedIn, and Telegram profiles

---

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/posts` | List all published posts |
| `GET` | `/api/posts/:slug` | Get a single post |
| `POST` | `/api/posts` | Create a post |
| `PUT` | `/api/posts/:slug` | Update a post |
| `DELETE` | `/api/posts/:slug` | Delete a post |
| `POST` | `/api/sync` | Trigger Notion sync (`X-Sync-Secret` header) |

---

## Bot monitoring

Every crawler visit is logged with a `[BOT]` prefix:

```
[BOT] 2026-05-29 14:32:11 | Googlebot  | GET /posts/my-post
[BOT] 2026-05-29 15:01:44 | Perplexity | GET /sitemap.xml
```

In Railway: **Deployments → active deploy → Deploy Logs** → filter by `[BOT]`.

---

## Stack

- [FastAPI](https://fastapi.tiangolo.com/) — web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) + PostgreSQL — database
- [Jinja2](https://jinja.palletsprojects.com/) — SSR templates with custom `[[ ]]` delimiters
- [APScheduler](https://apscheduler.readthedocs.io/) — weekly Notion sync
- [notion-client](https://github.com/ramnes/notion-sdk-py) — Notion API

---

## License

MIT — see [LICENSE](LICENSE).

Built by [Daniel Levinishnikov](https://llmceo.com).
