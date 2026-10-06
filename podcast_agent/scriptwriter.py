"""Step 2: turn the research briefing into a two-host dialogue script (structured JSON)."""

import json

from openai import OpenAI

from . import config

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "summary", "turns"],
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "turns": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["speaker", "text"],
                "properties": {
                    "speaker": {"type": "string", "enum": ["A", "B"]},
                    "text": {"type": "string"},
                },
            },
        },
    },
}


def word_count(script: dict) -> int:
    return sum(len(t["text"].split()) for t in script["turns"])


def write_script(briefing_md: str, date_window: str) -> dict:
    client = OpenAI(api_key=config.openai_api_key(), timeout=600)
    min_w, max_w = config.TARGET_WORDS
    instructions = (config.PROMPTS_DIR / "script.md").read_text().format(
        show_title=config.SHOW_TITLE,
        host_a=config.HOST_A_NAME,
        host_b=config.HOST_B_NAME,
        min_words=min_w,
        max_words=max_w,
    )
    user_input = f"Date window covered: {date_window}\n\nResearch briefing:\n\n{briefing_md}"

    response = client.responses.create(
        model=config.SCRIPT_MODEL,
        instructions=instructions,
        input=user_input,
        text={"format": {"type": "json_schema", "name": "podcast_script", "strict": True, "schema": SCHEMA}},
    )
    script = json.loads(response.output_text)

    words = word_count(script)
    if words < min_w * 0.6 or words > max_w * 1.5:
        print(f"[script] warning: {words} words, outside target {min_w}-{max_w}")
    if not script["turns"]:
        raise RuntimeError("Script writer returned no dialogue turns")
    return script
