"""Orchestrator: research → script → voice → publish → feed.

Usage:
  python -m podcast_agent.run                 # full weekly run (publishes)
  python -m podcast_agent.run --no-publish    # build everything locally, don't upload / touch the feed
  python -m podcast_agent.run --skip-tts      # research + script only (cheap test, no ElevenLabs credits)
  python -m podcast_agent.run --fresh         # ignore cached briefing/script for this week
  python -m podcast_agent.run --force         # re-run even if this week's episode is already published
"""

import argparse
import json
import sys
from datetime import datetime, timedelta

from . import config
from .feed import load_index, save_index, write_feed


def episode_id(now: datetime) -> str:
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def previous_episode(index: list[dict], current_id: str) -> dict | None:
    prior = [e for e in index if e["id"] != current_id]
    return max(prior, key=lambda e: e["pub_date_iso"]) if prior else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-publish", action="store_true")
    ap.add_argument("--skip-tts", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    now = datetime.now(config.LONDON).replace(microsecond=0)
    ep_id = episode_id(now)
    index = load_index()
    if any(e["id"] == ep_id for e in index) and not args.force:
        print(f"Episode {ep_id} already published; nothing to do (use --force to redo).")
        return 0

    ep_dir = config.EPISODES_DIR / ep_id
    ep_dir.mkdir(parents=True, exist_ok=True)
    prev = previous_episode(index, ep_id)
    since = datetime.fromisoformat(prev["pub_date_iso"]) if prev else now - timedelta(days=7)
    window = f"{since:%a %d %b %Y %H:%M} to {now:%a %d %b %Y %H:%M} UK time"
    week_label = f"week to {now:%d %B %Y}"

    # 1. Research
    briefing_file, sources_file = ep_dir / "briefing.md", ep_dir / "sources.json"
    if briefing_file.exists() and not args.fresh:
        print(f"[research] reusing {briefing_file.relative_to(config.ROOT)}")
        briefing = briefing_file.read_text()
        sources = json.loads(sources_file.read_text()) if sources_file.exists() else []
    else:
        from .research import run_research

        prev_text = None
        if prev and (config.EPISODES_DIR / prev["id"] / "briefing.md").exists():
            prev_text = (config.EPISODES_DIR / prev["id"] / "briefing.md").read_text()
        print(f"[research] {config.RESEARCH_MODEL} researching {window} …")
        result = run_research(now, since, week_label, prev_text)
        briefing, sources = result.markdown, result.sources
        briefing_file.write_text(briefing + "\n")
        sources_file.write_text(json.dumps(sources, indent=2, ensure_ascii=False) + "\n")
        print(f"[research] {len(briefing)} chars, {len(sources)} cited sources")

    # 2. Script
    script_file = ep_dir / "script.json"
    if script_file.exists() and not args.fresh:
        print(f"[script] reusing {script_file.relative_to(config.ROOT)}")
        script = json.loads(script_file.read_text())
    else:
        from .scriptwriter import word_count, write_script

        print(f"[script] {config.SCRIPT_MODEL} writing dialogue …")
        script = write_script(briefing, window)
        script_file.write_text(json.dumps(script, indent=2, ensure_ascii=False) + "\n")
        print(f"[script] “{script['title']}” — {len(script['turns'])} turns, {word_count(script)} words")

    if args.skip_tts:
        print("Stopping before TTS (--skip-tts).")
        return 0

    # 3. Voice
    from .tts import synthesize

    config.BUILD_DIR.mkdir(exist_ok=True)
    mp3 = config.BUILD_DIR / f"weekly-market-brief-{ep_id}.mp3"
    duration = synthesize(script, mp3)
    print(f"[tts] wrote {mp3.relative_to(config.ROOT)} ({duration / 60:.1f} min, {mp3.stat().st_size / 1e6:.1f} MB)")

    if args.no_publish:
        print("Not publishing (--no-publish).")
        return 0

    # 4. Publish audio + 5. update feed
    from .publish import upload_release

    tag = f"ep-{ep_id}"
    title = f"{now:%d %b %Y}: {script['title']}"
    briefing_url = f"https://github.com/{config.GITHUB_REPOSITORY}/blob/main/episodes/{ep_id}/briefing.md"
    audio_url = upload_release(tag, title, f"{script['summary']}\n\nWritten briefing: {briefing_url}", mp3)
    print(f"[publish] {audio_url}")

    index = [e for e in index if e["id"] != ep_id]
    index.append(
        {
            "id": ep_id,
            "guid": f"{config.GITHUB_REPOSITORY}:{tag}",
            "title": title,
            "summary": script["summary"],
            "pub_date_iso": now.isoformat(),
            "audio_url": audio_url,
            "audio_bytes": mp3.stat().st_size,
            "duration_seconds": round(duration, 1),
            "briefing_url": briefing_url,
            "sources": sources,
        }
    )
    save_index(index)
    write_feed(index)
    print(f"[feed] updated docs/feed.xml ({len(index)} episodes) → {config.SITE_URL}/feed.xml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
