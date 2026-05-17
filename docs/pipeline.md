# pipeline

End-to-end stage diagram + per-stage rationale.

## Diagram

```
  IMG_*.MOV (portrait phone vids)
        │
        │  transcribe.py  (faster-whisper medium.en, parallel x3)
        ▼
  work/transcripts/IMG_*.json   (word-level timestamps)
        │
        │  HUMAN: read transcripts, pick punchlines
        ▼
  manifest.json   (per-speaker name / topic / t_in / t_out)
        │
        ├────────────────────────────┐
        │                            │
        │  cut_clip.py               │  render_intro.py
        ▼                            ▼
  work/cuts_plain/c_NN.mp4       work/intro.mp4 (5s)
        │                            │
        │  overlay_one_cut.py        │
        │   ├ slice word_jsons       │
        │   └ overlay_terminal.py    │  render_outro.py
        ▼                            ▼
  work/cuts_overlaid/c_NN.mp4    work/outro.mp4 (5s)
        │                            │
        └────────────┬───────────────┘
                     │
                     │  concat_reel.py
                     │   filter_complex single pass
                     │   per-seg apad,atrim
                     │   vignette=PI/5
                     │   final loudnorm
                     ▼
            renders/reel.mp4   (vertical 1080x1920)
```

## Stage 1: Transcribe

`scripts/transcribe.py`

- faster-whisper `medium.en`, `compute_type="int8"` on CPU (M-series
  Macs do this in ~real-time)
- `word_timestamps=True` is critical for per-word reveal in the overlay
- `vad_filter=True` to skip silence
- Parallel via `ProcessPoolExecutor`, 3 workers. More workers don't
  help much because of int8 int-throughput; memory bandwidth caps it.
- Patch dict for whisper mishears: `"cloud" -> "Claude"` is the most
  common one in AI-builder contexts. Extend per event.

## Stage 2: Manifest

Human-curated JSON. The AI cannot reliably pick punchlines . it
doesn't know which line is funny, which is the actual product pitch,
which has dead air after it. Read the transcripts (10-20 lines each),
pick 5-15s windows that:

1. Start at the speaker's "I'm X" or "My name is X" (or skip the intro
   if the toast covers the name)
2. End on a complete thought (punchline, product name, joke landing)
3. Avoid filler ("um", "like", "you know") . `overlay_terminal.py` has
   a `drop_words` config to strip those from subs but the audio keeps
   them
4. Are punchy: <10s per speaker for energy; <15s for richness

## Stage 3: Cut

`scripts/cut_clip.py`

Per-clip single-pass ffmpeg:
- auto-rotate (NO `-noautorotate`, NO manual `transpose`)
- `scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920`
- `eq=contrast=1.06:saturation=1.08:gamma=0.98` (mild grade . phones
  underexpose in indoor venue lighting)
- audio: `loudnorm=I=-16:TP=-3:LRA=11` (PER-CLIP loudnorm; you'll do
  another pass at concat time)
- **NO `silenceremove`** (sync bug . see `gotchas.md`)
- libx264 yuv420p crf 18 preset medium, 192k AAC stereo, +faststart

Output: `work/cuts_plain/c_NN.mp4` . plain talking head, no captions.

## Stage 4: Overlay

`scripts/overlay_one_cut.py` per clip:

1. **Slice word JSON**: read source-source whisper output, keep words
   where `start >= t_in AND end <= t_out`, shift starts/ends by `-t_in`
   so cut-relative time starts at 0.
2. **Write per-cut YAML config** for `overlay_terminal.py`:
   - One toast: `slug, label="> NAME", topic, t_start=0.20`
   - One subtitle entry: `words_json, v_start=0, v_end=cut_dur`
   - Vertical tuning: `fixed_panel_w=1020, sub_bottom_margin=220,
     toast_top_margin=110`
3. **Invoke overlay_terminal.py**: cv2 per-frame composite reads the
   plain mp4, composites the toast (PIL-rendered PNG) + subtitle panel
   (PIL-rendered per phrase, cached by `(phrase_idx, n_visible, cursor_on)`)
   onto each frame, pipes raw BGR24 to ffmpeg libx264, then muxes the
   original audio with `-c copy`.

Why cv2 per-frame: ffmpeg `-loop 1 -i toast.png + overlay` chained 3+
times produces a runaway encode (we tried it; ~hours of CPU and
multi-GB output for a 60s reel). cv2 per-frame at 30 fps for 7s = 210
frames, takes ~10s with PIL frame caching.

Output: `work/cuts_overlaid/c_NN.mp4` . toast + subs baked in, audio
preserved bit-for-bit.

## Stage 5: Concat

`scripts/concat_reel.py`

Single `filter_complex` pass over all inputs (intro + N cuts + outro):
- per-input video chain: `scale + crop + setsar + fps=30 + setpts`
- per-input audio chain:
  `aresample=44100,aformat=channel_layouts=stereo,apad,atrim=duration={video_dur:.6f},asetpts`
  The `apad,atrim=duration=X` is THE fix for AAC concat drift.
- `concat=n=N+2:v=1:a=1`
- post: `vignette=PI/5` on video, final `loudnorm=I=-16:TP=-3:LRA=11`
  on audio
- output: libx264 yuv420p crf 18 preset slow, 192k AAC stereo,
  +faststart

This is a single-pass concat (no intermediate files), keeps quality
high and avoids accumulation losses across multiple re-encodes.

## Intro / outro

Both are PIL → PNG sequence → ffmpeg image2 → mp4 pipelines, NOT pure
ffmpeg drawtext. Why: emoji rendering (see `gotchas.md`) and complex
timing (typewriter reveal, fade-in, scale-up, breath pulse) are
cleaner in Python than in chained `enable=between(t,a,b)` expressions.

Parameterize:
- Event name + tagline
- Palette accent color
- Status block lines (location, vibe, etc.)
- Prize line (outro)
- Lobster emoji or your event's mascot

## Wall clock on the Ralphthon submission

Per-stage timings, M3 Max, 9 speakers:
- Transcribe (parallel x3): ~2 min for ~3 min total audio
- Manual punchline pick: ~5 min reading transcripts
- Cut (sequential, 9 clips): ~30s total
- Overlay (sequential, 9 clips): ~3 min total (cv2 dominated)
- Intro + outro (background agents, parallel): ~5 min
- Concat: ~20s

Total: ~15-20 min from raw MOV to final mp4. Most of that is the
overlay step, which is trivially parallelizable (each clip is
independent) . a future PR.
