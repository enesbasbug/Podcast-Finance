"""Central configuration. Everything secret or tunable comes from env vars (.env locally, GitHub Secrets/Variables in CI)."""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional in CI
    pass

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
EPISODES_DIR = ROOT / "episodes"
DOCS_DIR = ROOT / "docs"
BUILD_DIR = ROOT / "build"
INDEX_FILE = EPISODES_DIR / "index.json"

LONDON = ZoneInfo("Europe/London")


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# --- API keys (read lazily so --help etc. work without them) ---
def openai_api_key() -> str:
    return _env("OPENAI_API_KEY")


def elevenlabs_api_key() -> str:
    return _env("ELEVENLABS_API_KEY")


# --- Models ---
RESEARCH_MODEL = os.environ.get("RESEARCH_MODEL") or "gpt-5.5"
RESEARCH_REASONING = os.environ.get("RESEARCH_REASONING") or "medium"  # low | medium | high
SCRIPT_MODEL = os.environ.get("SCRIPT_MODEL") or "gpt-5.5"

# --- Voices (defaults: ElevenLabs premade British voices "George" and "Alice") ---
HOST_A_NAME = os.environ.get("HOST_A_NAME") or "George"
HOST_B_NAME = os.environ.get("HOST_B_NAME") or "Alice"
VOICE_A_ID = os.environ.get("VOICE_A_ID") or "JBFqnCBsd6RMkjVDRZzb"
VOICE_B_ID = os.environ.get("VOICE_B_ID") or "Xb7hH8MSUJpSbSDYk0k2"
TTS_MODEL = os.environ.get("TTS_MODEL") or "eleven_v3"
TTS_FALLBACK_MODEL = os.environ.get("TTS_FALLBACK_MODEL") or "eleven_multilingual_v2"
DIALOGUE_CHUNK_CHARS = int(os.environ.get("DIALOGUE_CHUNK_CHARS") or 1800)  # API recommends <= 2000

# --- Show metadata (used in the RSS feed) ---
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY") or "enesbasbug/Podcast-Finance"
_owner, _repo = GITHUB_REPOSITORY.split("/", 1)
SITE_URL = (os.environ.get("SITE_URL") or f"https://{_owner.lower()}.github.io/{_repo}").rstrip("/")

SHOW_TITLE = os.environ.get("SHOW_TITLE") or "The Weekly Market Brief"
SHOW_AUTHOR = os.environ.get("SHOW_AUTHOR") or "Enes Basbug"
SHOW_OWNER_EMAIL = os.environ.get("SHOW_OWNER_EMAIL") or ""  # Spotify/Apple email this to verify ownership
SHOW_LANGUAGE = os.environ.get("SHOW_LANGUAGE") or "en-gb"
SHOW_DESCRIPTION = os.environ.get("SHOW_DESCRIPTION") or (
    "A weekly, source-checked briefing on markets, the economy and company earnings for UK retail "
    "investors, released every Monday morning. General information only, not personal financial advice. "
    "Researched and voiced with AI."
)
SHOW_CATEGORY = ("Business", "Investing")

TARGET_WORDS = (int(os.environ.get("TARGET_WORDS_MIN") or 850), int(os.environ.get("TARGET_WORDS_MAX") or 1300))
