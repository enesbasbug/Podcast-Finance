# The Weekly Market Brief — AI podcast agent

Every Monday at 10:00 UK time, a GitHub Action:

1. **Researches** the past week with an OpenAI model plus web search, using the briefing prompt in `podcast_agent/prompts/research.md`. It writes `episodes/<week>/briefing.md` with citations.
2. **Writes** a two-host conversation (`script.json`) from that briefing, using `prompts/script.md`.
3. **Voices** it with ElevenLabs Text-to-Dialogue (`eleven_v3`), then masters one MP3 with ffmpeg (-16 LUFS).
4. **Publishes** the MP3 as a GitHub Release asset and updates the RSS feed in `docs/feed.xml`, which GitHub Pages serves.

Spotify and Apple Podcasts read that RSS feed, so new episodes show up there automatically. Hosting is free. You only pay for the OpenAI and ElevenLabs usage.

```
podcast_agent/
  config.py        env-driven settings (models, voices, show metadata)
  research.py      OpenAI Responses API + web_search
  scriptwriter.py  briefing → JSON dialogue (structured output)
  tts.py           ElevenLabs dialogue (≤2k chars/request) + ffmpeg mastering, per-line TTS fallback
  feed.py          episodes/index.json → docs/feed.xml (Apple/Spotify tags)
  publish.py       gh release upload
  run.py           orchestrator (python -m podcast_agent)
docs/              GitHub Pages site: feed.xml, cover.jpg, index.html
episodes/          per-week briefing.md, sources.json, script.json + index.json
```

## One-time setup

1. **Push to a public GitHub repo.** The free Pages and Actions tiers need a public repo. Your API keys stay private as Secrets.
2. **Settings → Secrets and variables → Actions**
   - Secrets: `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`
   - Variables:
     - `SHOW_OWNER_EMAIL` (required for the Spotify/Apple ownership check; it appears publicly in the feed)
     - Optional: `SHOW_TITLE`, `SHOW_AUTHOR`, `RESEARCH_MODEL`, `SCRIPT_MODEL`, `VOICE_A_ID`, `VOICE_B_ID`, `HOST_A_NAME`, `HOST_B_NAME`
3. **Settings → Pages → Source: GitHub Actions.**
4. **Actions → Weekly episode → Run workflow** to make the first episode now.
5. Check the feed at `https://<user>.github.io/<repo>/feed.xml`:
   - Validate it at https://www.castfeedvalidator.com.
   - Optionally test it privately in Apple Podcasts (Library → ⋯ → *Follow a Show by URL*).
6. **Submit the feed once.**
   - Spotify: https://creators.spotify.com → *Get started* → *Find an existing show* → paste the RSS URL → enter the code sent to `SHOW_OWNER_EMAIL`.
   - Apple: https://podcastsconnect.apple.com → **+** → *New Show* → *Add a show with an RSS feed*. Review takes about 1–5 days.

## Local runs

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # add your keys
.venv/bin/python -m podcast_agent --skip-tts     # research + script only (no ElevenLabs credits)
.venv/bin/python -m podcast_agent --no-publish   # full audio into build/, nothing uploaded
```

Results for the current ISO week are cached, so re-runs reuse `briefing.md` and `script.json`. Use `--fresh` to regenerate them and `--force` to republish a week that's already out.

## Tuning

- **Voices:** pick any two voice IDs from your ElevenLabs Voice Library and set `VOICE_A_ID` and `VOICE_B_ID`. Hosts are unnamed by default; set `HOST_A_NAME` and `HOST_B_NAME` if you want them to introduce themselves.
- **Length:** set `TARGET_WORDS_MIN` and `TARGET_WORDS_MAX`. The defaults of 550–750 words give about 5 minutes (the voices speak at about 120 words a minute).
- **Tone and structure:** edit `podcast_agent/prompts/script.md`.

## Costs (rough)

- **OpenAI:** about $0.30–$1 per episode (research with web search plus scripting).
- **ElevenLabs:** about 4–5k characters per episode, or 16–22k a month. A public podcast needs a paid plan with a commercial licence; Starter (30k a month) is enough.
