"""Episode index (episodes/index.json) and RSS feed generation (docs/feed.xml) for Apple Podcasts / Spotify."""

import html
import json
from datetime import datetime
from email.utils import format_datetime
from xml.sax.saxutils import escape

from . import config

DISCLAIMER = (
    "General information only, not personal financial advice. Do your own research and consider "
    "speaking to a regulated adviser. Researched with AI web search and voiced with AI voices; "
    "facts can be wrong — check the linked sources."
)


def load_index() -> list[dict]:
    if config.INDEX_FILE.exists():
        return json.loads(config.INDEX_FILE.read_text())
    return []


def save_index(episodes: list[dict]) -> None:
    config.INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.INDEX_FILE.write_text(json.dumps(episodes, indent=2, ensure_ascii=False) + "\n")


def show_notes_html(ep: dict, max_sources: int = 30) -> str:
    parts = [f"<p>{html.escape(ep['summary'])}</p>"]
    if ep.get("briefing_url"):
        parts.append(f'<p><a href="{html.escape(ep["briefing_url"])}">Full written briefing with citations</a></p>')
    sources = ep.get("sources") or []
    if sources:
        items = "".join(
            f'<li><a href="{html.escape(s["url"])}">{html.escape(s["title"])}</a></li>' for s in sources[:max_sources]
        )
        parts.append(f"<p>Sources:</p><ul>{items}</ul>")
    parts.append(f"<p><em>{html.escape(DISCLAIMER)}</em></p>")
    return "".join(parts)


def _hms(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def render_feed(episodes: list[dict]) -> str:
    cover = f"{config.SITE_URL}/cover.jpg"
    feed_url = f"{config.SITE_URL}/feed.xml"
    cat, subcat = config.SHOW_CATEGORY
    now = format_datetime(datetime.now(config.LONDON))

    items = []
    for ep in sorted(episodes, key=lambda e: e["pub_date_iso"], reverse=True):
        pub = format_datetime(datetime.fromisoformat(ep["pub_date_iso"]))
        notes = show_notes_html(ep)
        items.append(
            f"""    <item>
      <title>{escape(ep['title'])}</title>
      <description><![CDATA[{notes}]]></description>
      <content:encoded><![CDATA[{notes}]]></content:encoded>
      <itunes:summary>{escape(ep['summary'])}</itunes:summary>
      <enclosure url="{escape(ep['audio_url'])}" length="{ep['audio_bytes']}" type="audio/mpeg"/>
      <guid isPermaLink="false">{escape(ep['guid'])}</guid>
      <pubDate>{pub}</pubDate>
      <itunes:duration>{_hms(ep['duration_seconds'])}</itunes:duration>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
      <link>{escape(ep.get('briefing_url') or config.SITE_URL)}</link>
    </item>"""
        )

    owner_email = (
        f"\n      <itunes:email>{escape(config.SHOW_OWNER_EMAIL)}</itunes:email>" if config.SHOW_OWNER_EMAIL else ""
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>{escape(config.SHOW_TITLE)}</title>
    <link>{escape(config.SITE_URL)}/</link>
    <atom:link href="{escape(feed_url)}" rel="self" type="application/rss+xml"/>
    <language>{config.SHOW_LANGUAGE}</language>
    <copyright>© {datetime.now().year} {escape(config.SHOW_AUTHOR)}</copyright>
    <description>{escape(config.SHOW_DESCRIPTION)}</description>
    <itunes:summary>{escape(config.SHOW_DESCRIPTION)}</itunes:summary>
    <itunes:author>{escape(config.SHOW_AUTHOR)}</itunes:author>
    <itunes:owner>
      <itunes:name>{escape(config.SHOW_AUTHOR)}</itunes:name>{owner_email}
    </itunes:owner>
    <itunes:image href="{escape(cover)}"/>
    <image><url>{escape(cover)}</url><title>{escape(config.SHOW_TITLE)}</title><link>{escape(config.SITE_URL)}/</link></image>
    <itunes:category text="{escape(cat)}"><itunes:category text="{escape(subcat)}"/></itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <podcast:locked>no</podcast:locked>
    <lastBuildDate>{now}</lastBuildDate>
    <generator>podcast_agent</generator>
{chr(10).join(items)}
  </channel>
</rss>
"""


def write_feed(episodes: list[dict]) -> None:
    config.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (config.DOCS_DIR / "feed.xml").write_text(render_feed(episodes))
