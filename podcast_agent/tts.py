"""Step 3: voice the dialogue with ElevenLabs and master a single MP3 with ffmpeg."""

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from . import config

TAG_RE = re.compile(r"\[[^\]]{1,40}\]\s*")
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")


def _voice(speaker: str) -> str:
    return config.VOICE_A_ID if speaker == "A" else config.VOICE_B_ID


def _split_long_turns(turns: list[dict], limit: int) -> list[dict]:
    out = []
    for turn in turns:
        if len(turn["text"]) <= limit:
            out.append(turn)
            continue
        buf = ""
        for sentence in SENTENCE_RE.split(turn["text"]):
            if buf and len(buf) + len(sentence) + 1 > limit:
                out.append({"speaker": turn["speaker"], "text": buf})
                buf = ""
            buf = f"{buf} {sentence}".strip()
        if buf:
            out.append({"speaker": turn["speaker"], "text": buf})
    return out


def chunk_turns(turns: list[dict], limit: int) -> list[list[dict]]:
    """Group consecutive turns so each Text-to-Dialogue request stays under the character limit."""
    chunks, current, size = [], [], 0
    for turn in _split_long_turns(turns, limit):
        n = len(turn["text"])
        if current and size + n > limit:
            chunks.append(current)
            current, size = [], 0
        current.append(turn)
        size += n
    if current:
        chunks.append(current)
    return chunks


def _dialogue_chunk(client, chunk: list[dict]) -> bytes:
    from elevenlabs import DialogueInput

    audio = client.text_to_dialogue.convert(
        inputs=[DialogueInput(text=t["text"], voice_id=_voice(t["speaker"])) for t in chunk],
        model_id=config.TTS_MODEL,
        output_format="mp3_44100_128",
    )
    return b"".join(audio)


def _per_turn_chunk(client, chunk: list[dict]) -> list[bytes]:
    """Fallback: classic TTS one turn at a time (audio tags stripped, since v2 models would read them)."""
    parts = []
    for t in chunk:
        text = TAG_RE.sub("", t["text"]).strip()
        if not text:
            continue
        audio = client.text_to_speech.convert(
            voice_id=_voice(t["speaker"]),
            text=text,
            model_id=config.TTS_FALLBACK_MODEL,
            output_format="mp3_44100_128",
        )
        parts.append(b"".join(audio))
    return parts


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def master(parts: list[Path], out_path: Path) -> None:
    """Concatenate parts, normalise to podcast loudness (-16 LUFS), encode 128 kbps MP3."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as listing:
        for p in parts:
            listing.write(f"file '{p.resolve()}'\n")
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", listing.name,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "44100", "-ac", "2", "-codec:a", "libmp3lame", "-b:a", "128k",
            str(out_path),
        ],
        check=True,
    )
    Path(listing.name).unlink(missing_ok=True)


def check_quota(client, needed_chars: int) -> None:
    """Fail before spending anything if the ElevenLabs plan can't cover this episode (1 credit ≈ 1 character)."""
    try:
        sub = client.user.subscription.get()
    except Exception as exc:  # noqa: BLE001 — keys without the user_read permission can't see their balance
        print(f"[tts] couldn't read ElevenLabs credit balance ({getattr(exc, 'status_code', exc)}); continuing")
        return
    remaining = sub.character_limit - sub.character_count
    print(f"[tts] ElevenLabs {sub.tier}: {remaining:,} of {sub.character_limit:,} credits left, episode needs ~{needed_chars:,}")
    if remaining < needed_chars:
        raise RuntimeError(f"Not enough ElevenLabs credits: {remaining:,} left, ~{needed_chars:,} needed")


def synthesize(script: dict, out_path: Path) -> float:
    """Render the script to out_path. Returns duration in seconds.

    Each chunk's audio is cached under a folder keyed by the script's hash, so a failed run can be retried
    without paying again for chunks that already succeeded.
    """
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=config.elevenlabs_api_key(), timeout=300)
    chunks = chunk_turns(script["turns"], config.DIALOGUE_CHUNK_CHARS)
    digest = hashlib.sha256(json.dumps([script["turns"], config.VOICE_A_ID, config.VOICE_B_ID, config.TTS_MODEL]).encode()).hexdigest()[:12]
    work = out_path.parent / f"{out_path.stem}_parts_{digest}"
    work.mkdir(parents=True, exist_ok=True)

    todo = [i for i in range(len(chunks)) if not list(work.glob(f"{i:03d}_*.mp3"))]
    needed = sum(len(t["text"]) for i in todo for t in chunks[i])
    print(f"[tts] {len(script['turns'])} turns in {len(chunks)} chunk(s); {len(chunks) - len(todo)} cached, {len(todo)} to generate")
    if todo:
        check_quota(client, needed)

    for i in todo:
        chunk = chunks[i]
        try:
            blobs = [_dialogue_chunk(client, chunk)]
        except Exception as exc:  # noqa: BLE001 — model/API hiccups fall back to per-turn TTS
            status, body = getattr(exc, "status_code", None), getattr(exc, "body", None)
            if status in (401, 402, 403) or "quota" in str(body):
                raise RuntimeError(f"ElevenLabs refused the request (HTTP {status}): {body}") from exc
            print(f"[tts] chunk {i} dialogue failed (HTTP {status}: {body}); falling back to {config.TTS_FALLBACK_MODEL}")
            blobs = _per_turn_chunk(client, chunk)
        for j, blob in enumerate(blobs):
            (work / f"{i:03d}_{j:03d}.mp3").write_bytes(blob)
        print(f"[tts] chunk {i + 1}/{len(chunks)} done")

    master(sorted(work.glob("*.mp3")), out_path)
    return ffprobe_duration(out_path)
