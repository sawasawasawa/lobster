# 🦞 lobster

**Turn a stack of phone interviews into a cinematic 60-80s vertical reel
before the closing ceremony.**

[![demo](https://img.shields.io/badge/▶_watch_the_demo-Ralphthon_%40SG_2026-D9533F)](https://www.youtube.com/shorts/62PI1G-wKN0)

> 9 builders. 69 seconds. ~20 minutes of wall clock from raw phone vids
> to a posted YouTube short. Terminal-style typewriter captions, generated
> intro and outro cards, lobster aesthetic baked in.

> Watch the actual submission: **https://www.youtube.com/shorts/62PI1G-wKN0**

## Why this exists

Hackathons end faster than your editing instincts. You have an hour of
phone interviews, a closing ceremony in 90 minutes, and zero patience for
DaVinci Resolve. lobster is the opinionated, terminal-flavored pipeline
that says: pick the 5-15 second punchlines, hit run, ship the link.

What you get:

- **Top-left agent toast**: yellow border, terminal close-X, slides in
  with the speaker's name + their one-liner topic
- **Bottom subtitle panel**: 3 traffic-light dots, `>_` prompt, per-word
  reveal synced to whisper timestamps, blinking cursor
- **Generated intro card**: event name typed out, status block, your
  mascot emoji, fade-into-the-first-clip handoff
- **Generated outro card**: dry-irony SQL shell, `SELECT winner FROM
  yourevent;`, redacted result, big lobster-red headline
- **Single-pass concat**: filter_complex with apad/atrim drift fix,
  vignette finish, loudnorm to -16 LUFS / -3 dBTP

No timeline app, no AI hallucination on the punchlines (you pick those),
no waiting for upload. Output is a single mp4 ready for YouTube Shorts,
TikTok, IG Reels, X.

## Install

```bash
git clone https://github.com/sawasawasawa/lobster.git
cd lobster
pip install -r requirements.txt
```

You also need `ffmpeg` 7+ on PATH (the `loudnorm` + `vignette` filters)
and JetBrains Mono Bold + Regular installed (auto-discovered from
`~/Library/Fonts/` on macOS; set `LOBSTER_FONT_BOLD` / `LOBSTER_FONT_REG`
env vars for any other path).

## Quickstart

Drop your phone videos somewhere (e.g. `sources/`). The pipeline assumes
portrait phone vids (1080x1920 effective, or 1920x1080 + `rotation=-90`
metadata . iPhone .MOV is the reference format).

### 1. Transcribe

```bash
python3 scripts/transcribe.py \
  --srcs sources/IMG_*.MOV \
  --out-dir work/transcripts
```

~real-time on M-series Macs (3 parallel workers).

### 2. Pick punchlines

Read each `work/transcripts/IMG_*.json`. Pick a 5-15s window per speaker.
Write a `manifest.json` like `examples/ralphthon-2026-manifest.json`:

```json
{
  "speakers": [
    {"idx": "01", "src": "sources/IMG_1082.MOV",
     "name": "Dan", "topic": "agentic Rube Goldberg across phones",
     "t_in": 1.85, "t_out": 8.30}
  ]
}
```

Guidance:

- Start `t_in` ~0.1s before the speaker's first word.
- End `t_out` on a complete thought (punchline lands, product name said).
- For the FIRST speaker, keep the "I'm X" intro (sets the format).
  For speakers 2+, you can skip "my name is..." since the toast shows
  the name . trims ~10s overall.
- Aim for 5-10s per speaker for energy, 10-15s for richness.

### 3. Cut + overlay each speaker

For each entry in your manifest, run two commands:

```bash
# Plain cut (rotate, scale to 1080x1920, color grade, loudnorm)
python3 scripts/cut_clip.py \
  --src sources/IMG_1082.MOV \
  --in 1.85 --out 8.30 \
  --idx 01 \
  --out-dir work/cuts_plain

# Overlay (slice word timestamps + terminal-style captions)
python3 scripts/overlay_one_cut.py \
  --cut work/cuts_plain/c_01.mp4 \
  --src-transcript work/transcripts/IMG_1082.json \
  --t-in 1.85 --t-out 8.30 \
  --name "Dan" \
  --topic "agentic Rube Goldberg across phones" \
  --idx 01 \
  --out work/cuts_overlaid/c_01.mp4
```

A simple bash loop reads the manifest and runs both per speaker.

### 4. Generate intro + outro

Both renderers have constants at the top of the file. Edit them for your
event, then run:

```bash
python3 scripts/render_intro.py    # writes work/intro/intro.mp4
python3 scripts/render_outro.py    # writes work/outro/outro.mp4
```

Things to change in `render_intro.py`: `TITLE_TEXT`, the subline, the
status block lines, the accent color (`TITLE` constant), the mascot
emoji.

Things to change in `render_outro.py`: `TITLE_TEXT` (the headline), the
SQL line, the result rows, the prize subtitle, the accent color.

Each renderer takes ~5s for 150 frames + ~1s for ffmpeg encode.

### 5. Concat

```bash
python3 scripts/concat_reel.py \
  --intro work/intro/intro.mp4 \
  --outro work/outro/outro.mp4 \
  --cuts-dir work/cuts_overlaid \
  --out renders/reel.mp4
```

Outputs vertical 1080x1920, 30fps, h264/aac, +faststart.

### 6. Watch

```bash
open renders/reel.mp4
```

Or upload directly: the output is sized and faststart-ed for YouTube
Shorts, TikTok, IG Reels, X.

## Files

```
scripts/
  transcribe.py         . faster-whisper medium.en, parallel
  cut_clip.py           . one ffmpeg pass per speaker
  overlay_one_cut.py    . slices word-jsons + invokes overlay_terminal
  overlay_terminal.py   . cv2 per-frame composite (toast + sub panel)
  render_intro.py       . PIL frame sequence . ffmpeg . event intro mp4
  render_outro.py       . PIL frame sequence . ffmpeg . event outro mp4
  concat_reel.py        . filter_complex concat + vignette + loudnorm
examples/
  ralphthon-2026-manifest.json   . the actual 9-speaker manifest
prompts/
  intro_agent.md, outro_agent.md, lobster_repo_agent.md
  . the literal coding-agent prompts used to generate the intro, outro,
    and this repo at Ralphthon. Useful starting points for new events.
docs/
  pipeline.md           . end-to-end stage diagram + rationale
  gotchas.md            . the lessons that cost the most time, read once
```

## Hard rules (the things that bit me)

- **Do NOT use ffmpeg `silenceremove`** in talking-head cut chains.
  Trims audio but not video . causes A/V desync. See `docs/gotchas.md`.
- **Apple Color Emoji + ffmpeg drawtext is incompatible.** Pre-render
  emoji to PNG via PIL, then composite.
- **AAC concat AV drift**: use `apad,atrim=duration=X` per segment
  before concat (`concat_reel.py` does this).
- **iPhone portrait sources**: trust ffmpeg auto-rotation, no manual
  `transpose`, no blur-pad.

Full lessons + reproductions in `docs/gotchas.md`.

## Tuning

- Vertical 1080x1920 is the default. For 4:3 1440x1080 (landscape
  event reels), change the overlay config:
  `fixed_panel_w=1320, sub_bottom_margin=70, toast_top_margin=60`.
- Toast hold time is 5s (`HOLD` constant in `overlay_terminal.py`).
  For longer cuts, bump it.
- The whisper patch dict (`PATCH` in `transcribe.py`) is empty by
  default. Add your event's most-mistranscribed product names so they
  come back correct in the subtitles.

## Hosts

Ralphthon @SG 2026 supported by OpenAI; hosted by Team Attention + Hashed.
Lobster mascot is theirs, used affectionately.

## License

MIT. See `LICENSE`.
