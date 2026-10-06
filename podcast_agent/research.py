"""Step 1: weekly web research with OpenAI (Responses API + web_search tool)."""

from dataclasses import dataclass
from datetime import datetime

from openai import OpenAI

from . import config


@dataclass
class Research:
    markdown: str
    sources: list[dict]  # [{"title": ..., "url": ...}] de-duplicated, in order of first citation


def _collect_sources(response) -> list[dict]:
    seen: dict[str, dict] = {}
    for item in response.output or []:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", None) or []:
            for ann in getattr(part, "annotations", None) or []:
                if getattr(ann, "type", None) == "url_citation" and ann.url not in seen:
                    seen[ann.url] = {"title": getattr(ann, "title", None) or ann.url, "url": ann.url}
    return list(seen.values())


def run_research(now: datetime, since: datetime, week_label: str, previous_briefing: str | None) -> Research:
    client = OpenAI(api_key=config.openai_api_key(), timeout=1800)
    instructions = (config.PROMPTS_DIR / "research.md").read_text()

    fmt = "%A %d %B %Y, %H:%M %Z"
    user_input = (
        f"Week label: {week_label}\n"
        f"Research cutoff (now): {now.strftime(fmt)}\n"
        f"Cover developments since: {since.strftime(fmt)}\n\n"
        "Previous briefing (for de-duplication and corrections):\n"
        "-----\n"
        f"{previous_briefing.strip() if previous_briefing else 'None — this is the first episode.'}\n"
        "-----"
    )

    response = client.responses.create(
        model=config.RESEARCH_MODEL,
        instructions=instructions,
        input=user_input,
        tools=[
            {
                "type": "web_search",
                "search_context_size": "high",
                "user_location": {"type": "approximate", "country": "GB", "city": "London", "timezone": "Europe/London"},
            }
        ],
        reasoning={"effort": config.RESEARCH_REASONING},
    )

    markdown = (response.output_text or "").strip()
    if len(markdown) < 500:
        raise RuntimeError(f"Research output suspiciously short ({len(markdown)} chars):\n{markdown}")
    return Research(markdown=markdown, sources=_collect_sources(response))
