# gotchas

Lessons that cost me hours the first time. Documenting them so future-me
(and you) don't pay the same tax twice.

## 1. ffmpeg `silenceremove` desyncs A/V in talking-head cuts

**Symptom**: viewer says "X's audio is out of sync with their mouth"
after a clip with internal pauses longer than ~1 second.

**Cause**: `silenceremove=stop_periods=-1:stop_silence=0.2:stop_threshold=-32dB`
in a per-clip audio filter chain trims silent regions from the AUDIO but
does NOT shorten the VIDEO. Audio gets shorter, video stays full length,
audio "races ahead" of the mouth.

**Fix**: do NOT use `silenceremove` in talking-head cut chains. Pick
cleaner `t_in / t_out` windows manually using word timestamps:
start ~0.1s before the first word, end ~0.1s after the last word.
Internal pauses are usually fine . emphasis pauses are good. If you
MUST collapse a long internal pause, do a two-cut concat (cut both
audio + video together), don't trim audio alone.

**Discovered**: Ralphthon v1, Mayank's clip had a 1.32s internal gap;
silenceremove collapsed it to 0.2s, audio became 1.12s shorter than
video, viewer immediately noticed.

## 2. Apple Color Emoji + ffmpeg drawtext is a dead end

**Symptom**: ffmpeg hangs or errors with
`Monochromatic (1bpp) fonts are not supported` when you include an
emoji like 🦞 in a drawtext `text=` argument with Apple Color Emoji as
fallback font.

**Cause**: Apple Color Emoji is a sbix (color-bitmap) font. ffmpeg's
drawtext uses libfreetype's VECTOR glyph pipeline, which cannot
rasterize bitmap-only fonts. The two pipelines are fundamentally
incompatible.

**Fix**: pre-render emoji glyphs via PIL at one of the supported sbix
sizes ({20, 32, 40, 48, 64, 96, 160} px) to a PNG, then composite via
ffmpeg `overlay=enable=between(t,A,B)`. Or build the entire card in
PIL → PNG sequence → ffmpeg image2 → mp4 (this is what
`render_intro.py` and `render_outro.py` do).

**Discovered**: Ralphthon intro/outro generation . both background
Engineer agents independently hit this and switched to PIL.

## 3. AAC concat AV drift over N segments

**Symptom**: lip-sync drift that grows as the reel plays. Frame N is
fine, frame 1800 is 50ms off.

**Cause**: AAC encoder pads each silent segment by ~8ms. With 8 concat
segments, that's ~64ms of audio-but-not-video. Default ffmpeg `concat`
filter doesn't enforce per-segment audio duration to match video
duration.

**Fix**: in `filter_complex` concat, apply
`apad,atrim=duration={video_duration:.6f}` to every segment's audio
chain before concat. See `scripts/concat_reel.py`.

**Discovered**: silent-card intros + interview clips were drifting ~60ms
by the end of an 8-segment concat; lip-sync started visibly off around
the 5th speaker.

## 4. iPhone portrait sources: no blur-pad, ever

**Symptom**: speaker appears small with blurred mirror-image bars on
the sides, or worse, rotated 90 degrees.

**Cause**: iPhone .MOV files are typically `1920x1080 + rotation=-90`
metadata. When ffmpeg auto-rotates, the decoded stream is 1080x1920
(portrait, upright). If you then `scale=1080:1920:force_original_aspect_ratio=decrease,pad=...`
to "fit", you're padding a portrait into a portrait . no-op. If you
ADD `transpose=1` thinking you need to rotate manually, you over-rotate
and turn the subject sideways.

**Fix**: trust auto-rotation. Verify with
`ffprobe -show_entries stream_side_data=rotation` before building the
pipeline. For portrait sources targeting portrait output:
`scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920`.
No transpose, no blur-pad.

**Discovered**: tried to pad a portrait into 1440x1080 4:3 with sampled
side-bars; result was identical to the unpadded source because the
source was already taller than wide. The pipeline is now portrait-out
only by default.

## 5. Pick a palette tied to the event mascot

The terminal aesthetic (deep near-black background, prompt-green text,
traffic-light dots) is fixed by `overlay_terminal.py`. The ACCENT color
(big headlines, agent name in toast) should match the event branding.

For Ralphthon 2026: lobster red `#D9533F` accent + prompt green
`#87C76B` text on near-black `#07090C` background.

For a new event: change the `TITLE` constant at the top of
`render_intro.py` and `render_outro.py`, and the `text_color` for the
toast label in `overlay_terminal.py` (currently `YELLOW`).

## 6. Light vignette PI/5 is the default finishing move

**Symptom**: reel feels flat after concat, even though every clip
looks fine standalone.

**Fix**: append `vignette=PI/5` after the concat filter. ~18% corner
darkening, cinematic, doesn't obscure captions. Standard for talking-
head finishes.

## 7. Final `loudnorm` peak target is -3 dBTP, NOT -1 dBTP

**Symptom**: ebur128 reports inter-sample true-peak of -0.8 dBTP even
though your loudnorm target was -1 dBTP.

**Cause**: AAC re-encoding lifts inter-sample true-peak by 1-2 dB
relative to the source PCM. If you ship at -1 dBTP target, you'll
clip on playback decoders.

**Fix**: target `TP=-3` in `loudnorm`. Final ebur128 will read close
to -3 dBFS, well within spec for any platform.
