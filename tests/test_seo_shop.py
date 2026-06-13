"""
SEO guards for the shop product surface (sitemap.xml + llms.txt).

The shop's per-product pages are real, server-rendered URLs (llmceo.com/shop/cap/<slug>),
so the canonical discovery surfaces must list them. These tests prove build_sitemap() and
build_llms() actually emit the 10 products and that backend/shop_products.py stays well-formed
— if someone drops the mirror or the slug shape drifts, this fails instead of silently
shipping an incomplete sitemap.

Pure stdlib (no DB, no jinja). Run standalone:  python3 tests/test_seo_shop.py
…or under pytest if you wire CI up later.
"""
import os
import re
import sys
from pathlib import Path

# The backend uses flat imports (`import config`, `import seo`) and runs from backend/.
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))
os.environ.setdefault("SITE_DOMAIN", "https://llmceo.com")  # deterministic URLs

import seo  # noqa: E402
import shop_products  # noqa: E402

PRODUCTS = shop_products.SHOP_PRODUCTS
BASE = seo.BASE


def test_shop_products_are_well_formed():
    assert PRODUCTS, "SHOP_PRODUCTS is empty"
    slugs = [p["slug"] for p in PRODUCTS]
    assert len(slugs) == len(set(slugs)), "duplicate slug in SHOP_PRODUCTS"
    for p in PRODUCTS:
        assert set(p) >= {"slug", "name", "desc"}, f"missing keys: {p}"
        assert re.fullmatch(r"[a-z0-9-]+", p["slug"]), f"non-url-safe slug: {p['slug']!r}"
        assert p["name"].strip() and p["desc"].strip(), f"blank name/desc: {p['slug']}"


def test_sitemap_lists_every_product():
    xml = seo.build_sitemap([])
    locs = set(re.findall(r"<loc>(.*?)</loc>", xml))
    for p in PRODUCTS:
        assert f"{BASE}/shop/cap/{p['slug']}" in locs, f"sitemap missing {p['slug']}"


def test_sitemap_keeps_core_pages():
    locs = set(re.findall(r"<loc>(.*?)</loc>", seo.build_sitemap([])))
    for path in ("/", "/posts.html", "/shop/"):
        assert f"{BASE}{path}" in locs, f"sitemap dropped {path}"


def test_product_urls_are_real_paths_not_hash():
    """Products must be linked as crawlable real paths — a '#' fragment is invisible to bots."""
    xml = seo.build_sitemap([])
    for p in PRODUCTS:
        assert f"/shop/#/cap/{p['slug']}" not in xml, f"{p['slug']} still hash-routed"
        assert f"{BASE}/shop/cap/{p['slug']}" in xml


def test_llms_has_shop_products_section():
    txt = seo.build_llms([])
    assert "## Shop products" in txt, "llms.txt missing the Shop products section"
    for p in PRODUCTS:
        line = f"- [{p['name']}]({BASE}/shop/cap/{p['slug']}): {p['desc']}"
        assert line in txt, f"llms.txt missing product line for {p['slug']}"


# ── standalone runner ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    print(f"seo-shop suite — {len(tests)} tests\n")
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
