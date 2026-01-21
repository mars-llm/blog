#!/usr/bin/env python3
"""Static blog builder for GitHub Pages.

- Input: Markdown posts in content/posts/*.md with YAML front matter.
- Output: dist/ directory.
- Templates: templates/*.html (Jinja2).

Designed for GitHub Pages project site at /blog/.
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import markdown2
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.S)
SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class Post:
    title: str
    date: dt.date
    slug: str
    url: str
    html: str
    excerpt: str
    tags: List[str]
    category: str
    level: str
    hero: str | None


def slugify(text: str) -> str:
    s = text.strip().lower()
    s = SLUG_RE.sub("-", s).strip("-")
    return s or "post"


def parse_front_matter(md: str, source: Path) -> Tuple[Dict[str, Any], str]:
    m = FM_RE.match(md)
    if not m:
        return {}, md
    fm_raw, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_raw) or {}
    except Exception as e:
        raise ValueError(f"Invalid YAML front matter in {source}: {e}")
    return fm, body


def md_to_html(md: str) -> str:
    # extras for nicer output
    return markdown2.markdown(md, extras=[
        "fenced-code-blocks",
        "tables",
        "strike",
        "task_list",
        "cuddled-lists",
        "metadata",
    ])


def extract_excerpt(html: str, limit: int = 180) -> str:
    # Remove tags and compress spaces
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def load_config() -> Dict[str, Any]:
    cfg = yaml.safe_load((ROOT / "site.yml").read_text(encoding="utf-8"))
    assert isinstance(cfg, dict)
    return cfg


def load_stats() -> Dict[str, Any]:
    """Load network stats from stats.json if it exists."""
    stats_file = ROOT / "stats.json"
    if stats_file.exists():
        try:
            import json
            return json.loads(stats_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"bitcoin": {}, "lightning": {}}


def ensure_dist() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)


def copy_assets() -> None:
    shutil.copytree(ASSETS, DIST / "assets")


def build_posts(cfg: Dict[str, Any]) -> List[Post]:
    posts_dir = CONTENT / "posts"
    posts: List[Post] = []

    for path in sorted(posts_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        fm, body = parse_front_matter(raw, path)

        title = str(fm.get("title") or path.stem)
        date_raw = fm.get("date")
        if date_raw:
            # allow YYYY-MM-DD
            date = dt.date.fromisoformat(str(date_raw))
        else:
            # support filename prefix YYYY-MM-DD-
            m = re.match(r"(\d{4}-\d{2}-\d{2})-", path.name)
            if not m:
                raise ValueError(f"Post {path} needs date in front matter or filename YYYY-MM-DD-*")
            date = dt.date.fromisoformat(m.group(1))

        slug = str(fm.get("slug") or slugify(title))
        category = str(fm.get("category") or "mining")
        tags = fm.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        tags = list(map(str, tags))
        level = str(fm.get("level") or "1-1")
        hero = fm.get("hero")

        html = md_to_html(body)
        excerpt = extract_excerpt(html)

        url = f"/posts/{slug}/"
        posts.append(Post(
            title=title,
            date=date,
            slug=slug,
            url=url,
            html=html,
            excerpt=excerpt,
            tags=tags,
            category=category,
            level=level,
            hero=str(hero) if hero else None,
        ))

    # newest first
    posts.sort(key=lambda p: p.date, reverse=True)
    return posts


def jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def make_url(base_url: str, path: str) -> str:
    # base_url like "/blog" or ""; path like "/assets/..." or "/posts/..." or "/"
    base = (base_url or "").rstrip("/")
    if path == "/":
        return f"{base}/" or "/"
    return f"{base}{path}"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_site(cfg: Dict[str, Any], posts: List[Post]) -> None:
    env = jinja_env()

    base_url = str(cfg["site"].get("base_url", ""))

    # Provide helper in templates
    env.globals["url"] = lambda p: make_url(base_url, p)
    env.globals["now"] = lambda: dt.datetime.utcnow().strftime("%Y")

    stats = load_stats()
    ctx_base = {
        "site": cfg["site"],
        "theme": cfg["theme"],
        "base_url": base_url,
        "stats": stats,
    }

    # Index
    tmpl = env.get_template("index.html")
    out = tmpl.render(**ctx_base, posts=posts[:12])
    write_text(DIST / "index.html", out)

    # Archive
    tmpl = env.get_template("archive.html")
    out = tmpl.render(**ctx_base, posts=posts)
    write_text(DIST / "archive" / "index.html", out)

    # About
    tmpl = env.get_template("about.html")
    out = tmpl.render(**ctx_base)
    write_text(DIST / "about" / "index.html", out)

    # Posts
    tmpl = env.get_template("post.html")
    for p in posts:
        out = tmpl.render(**ctx_base, post=p)
        write_text(DIST / "posts" / p.slug / "index.html", out)

    # RSS Feed
    tmpl = env.get_template("feed.xml")
    build_date = dt.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    out = tmpl.render(**ctx_base, posts=posts[:20], build_date=build_date)
    write_text(DIST / "feed.xml", out)


def main() -> None:
    import sys
    local_mode = "--local" in sys.argv

    cfg = load_config()

    # Override base_url for local testing
    if local_mode:
        cfg["site"]["base_url"] = ""
        print("Building in LOCAL mode (base_url='')")

    ensure_dist()
    copy_assets()
    posts = build_posts(cfg)
    render_site(cfg, posts)


if __name__ == "__main__":
    main()
