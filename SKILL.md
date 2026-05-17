---
name: lobster
description: Build an AA-style vertical hackathon-interview highlight reel from N portrait phone videos. Top-left agent toast + terminal-window per-word subtitles + generated event intro/outro cards. Use when the user hands you raw phone interviews from a hackathon, demo day, or similar event and asks for a 60-80s vertical reel.
---

# lobster . vertical hackathon reel kit

This skill is the distilled pipeline that built the Ralphthon @SG 2026
highlight reel. It assumes:

- Sources are portrait phone videos (1080x1920 effective; either native
  portrait or 1920x1080 with `rotation=-90` metadata)
- ~5-10 speakers, each saying their name + what they're building
- Output is a single vertical 1080x1920 mp4, ~60-80 seconds total
- Captions are AA × NS terminal-style: top-left agent toast +
  bottom traffic-light terminal panel with per-word reveal

## When to use

- "Cut this hackathon footage into a reel"
- "Same style as AA × NS but for [other event]"
- "9 phone interviews, 80 seconds, vertical, name + project per person"

## When NOT to use

- Landscape sources (use the AA × NS pipeline directly at 1440x1080 4:3)
- Need anonymized faces (use the AA skill's `pixelate.py`)
- Need word-perfect typewriter timing with master scribe sources (use
  the HyperFrames path in the AA skill)

## Pipeline (5 stages)

1. **Transcribe** . `scripts/transcribe.py`. faster-whisper medium.en,
   word-level timestamps, parallel x3 workers, ~real-time on CPU.
2. **Manifest** . human-curated JSON listing per-speaker
   `{src, name, topic, t_in, t_out}`. See
   `examples/ralphthon-2026-manifest.json`.
3. **Cut** . `scripts/cut_clip.py`. Single ffmpeg pass per clip:
   auto-rotate, scale to 1080x1920, light eq grade, loudnorm to
   -16 LUFS / -3 dBTP. **NO silenceremove** (causes A/V desync, see
   `docs/gotchas.md`).
4. **Overlay** . `scripts/overlay_one_cut.py` slices word timestamps for
   the cut window and invokes `scripts/overlay_terminal.py` (cv2
   per-frame composite) to add the agent toast + per-word subtitle
   panel.
5. **Concat** . `scripts/concat_reel.py`. Single filter_complex with
   per-segment `apad,atrim=duration=X` to prevent AAC concat drift,
   `vignette=PI/5` post-concat, final `loudnorm`.

Intro/outro cards: `scripts/render_intro.py` and `scripts/render_outro.py`
render 150 PIL frames each at 1080x1920 then pipe to ffmpeg.
Parameterize event name, prize line, palette.

## Reference event

Ralphthon @SG 2026 (`examples/ralphthon-2026-manifest.json`):
- 9 speakers, 64s of cuts + 5s intro + 5s outro = 74s reel
- Lobster red `#D9533F` accent (NOT AA orange . different event)
- Prompt green `#87C76B` for terminal text
- Deep near-black `#07090C` background

## Hard rules

- NO em dashes (U+2014) or en dashes (U+2013) in any text . code,
  drawtext, captions, README. PAI rule, applies repo-wide.
- NO blur-pad for portrait sources (see `docs/gotchas.md`).
- NO claim of "locked AA asset" . this kit generates NEW cards per event.

## See also

- `docs/pipeline.md` . full stage diagram + per-stage rationale
- `docs/gotchas.md` . the hard-won lessons (silenceremove desync, emoji
  + drawtext incompat, AAC concat drift, AA branding truth)
- `prompts/` . the actual agent prompts used to generate the Ralphthon
  intro and outro cards (good starting points for new events)
