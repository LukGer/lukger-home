#!/usr/bin/env python3
"""Fetch the latest xkcd article via blogwatcher and download the comic image."""
import html.parser
import os
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

BASE_DIR = Path.home()
BLOGWATCHER = BASE_DIR / "go" / "bin" / "blogwatcher"
DB_PATH = BASE_DIR / ".blogwatcher" / "blogwatcher.db"
IMAGE_DIR = Path(__file__).resolve().parents[1] / "tmp"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_FILE = IMAGE_DIR / "xkcd_latest.png"


class ComicImageParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_comic = False
        self.src = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and attrs.get("id") == "comic":
            self.in_comic = True
        elif self.in_comic and tag == "img" and self.src is None:
            self.src = attrs.get("src")

    def handle_endtag(self, tag):
        if tag == "div" and self.in_comic:
            self.in_comic = False


def run_scan() -> None:
    try:
        subprocess.run([str(BLOGWATCHER), "scan"], check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("blogwatcher scan failed") from exc


def fetch_latest_article() -> Optional[sqlite3.Row]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"blogwatcher database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    with conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.title,
                a.url,
                a.published_date,
                a.discovered_date,
                b.name AS blog_name
            FROM articles a
            JOIN blogs b ON a.blog_id = b.id
            ORDER BY
                COALESCE(a.published_date, a.discovered_date) DESC,
                a.discovered_date DESC,
                a.id DESC
            LIMIT 1
            """
        )
        return cursor.fetchone()


def download_comic_image(article_url: str) -> Path:
    try:
        with urllib.request.urlopen(article_url, timeout=20) as response:
            html_content = response.read().decode("utf-8", errors="ignore")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to fetch article page: {exc}") from exc
    parser = ComicImageParser()
    parser.feed(html_content)
    image_src = parser.src
    if not image_src:
        raise RuntimeError("comic image not found in article page")
    if image_src.startswith("//"):
        image_url = f"https:{image_src}"
    elif image_src.startswith("http"):
        image_url = image_src
    else:
        image_url = urllib.request.urljoin(article_url, image_src)
    try:
        with urllib.request.urlopen(image_url, timeout=30) as img_resp:
            data = img_resp.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to download comic image: {exc}") from exc
    IMAGE_FILE.write_bytes(data)
    return IMAGE_FILE


def format_article(row: sqlite3.Row) -> str:
    title = row["title"].strip()
    url = row["url"].strip()
    published_date = row["published_date"] or row["discovered_date"]
    published_date = published_date or "?"
    blog = row["blog_name"]
    return (
        f"xkcd daily update from {blog}: {title}\n"
        f"Published: {published_date}\n"
        f"Link: {url}"
    )


def main() -> int:
    try:
        run_scan()
    except Exception as exc:
        print(f"Failed to scan xkcd feed: {exc}", file=sys.stderr)
        return 1
    try:
        article = fetch_latest_article()
    except Exception as exc:
        print(f"Could not read latest article: {exc}", file=sys.stderr)
        return 1
    if not article:
        print("No articles in the xkcd feed yet.")
        return 0
    try:
        image_path = download_comic_image(article["url"])
    except Exception as exc:
        print(f"Failed to download comic image: {exc}", file=sys.stderr)
        image_path = None
    if image_path:
        print(f"IMAGE_PATH: {image_path}")
    print(format_article(article))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
