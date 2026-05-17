# Intro agent prompt . Ralphthon 2026

Verbatim prompt fed to a coding agent to generate the 5-second
`intro.mp4` for the Ralphthon submission. The agent ran in a worktree,
completed in ~5 minutes, produced 1080x1920 30fps mp4 at 72 KB, hit
every hard spec.

Reuse pattern: change the event context block + palette + card
timeline. Keep the hard specs + done definition.

---

You are generating a 5-second intro mp4 for a hackathon highlight reel.
NO QUESTIONS . execute. Write the final file to:

`<absolute_path>/work/intro/intro.mp4`

## Hard specs

- Resolution: **1080x1920 vertical**
- Duration: 5.0s exactly
- fps: 30
- Codec: libx264 -pix_fmt yuv420p -crf 18 -preset slow
- Audio: silent stereo AAC 44.1kHz 192k (use `anullsrc=channel_layout=stereo:sample_rate=44100`)
- Container: .mp4 with `+faststart`

## Event context

- **Ralphthon @SG supported by OpenAI** (Singapore, today)
- Hosted by Team Attention + Hashed
- Lobster mascot . emoji 🦞 is on-brand
- AI hackathon, builder energy
- Prizes: $10k OpenAI API credits, 6mo ChatGPT Pro, $3k Network School credits

## Visual identity

Build a fresh intro for RALPHTHON. The card progression I want over 5s:

- t=0.0-0.6s . terminal cursor blinks, `> init ralphthon...` types in
  (green text)
- t=0.6-2.0s . title "RALPHTHON" appears in big pixel-block / blocky
  letters; subline `@ SG . supported by OpenAI` fades in beneath in
  lighter mono text
- t=2.0-3.5s . small status block bottom-left:
  ```
  status: 6 builders interviewed
  location: suntec t1 . level 33
  vibe: ⚡ lobster-coded 🦞
  ```
- t=3.5-5.0s . hold + subtle scanline pulse, then a soft 0.3s
  fade-to-near-black at the very end so it crossfades into clip 1

## Palette

- Background: deep near-black `#07090C` with very faint scanline / dot
  grid
- Primary terminal text: `>_` prompt green `#87C76B`
- RALPHTHON title accent: lobster red `#D9533F`
- Subtle accents: cool white `#E8EEF5`
- NEVER use pure black

## Tools you can use (your choice . pick whatever is fastest)

1. **Pure ffmpeg with drawtext/drawbox**: fastest path. Use multiple
   drawtext filters with `enable='between(t,a,b)'` for timed reveals.
   JetBrains Mono Bold at
   `~/Library/Fonts/JetBrainsMonoNL-Bold.ttf`.
2. **PIL > 150 PNGs > ffmpeg image2 > mp4**: better typography control
   if needed.
3. **HTML/CSS > headless chromium > mp4**: most flexible but slowest
   to spin up. Skip unless 1+2 fail.

## Constraints

- NO em dashes (U+2014) or en dashes (U+2013) anywhere in the rendered
  text. Use periods, commas, dots, or `·` (U+00B7).
- The title text MUST be exactly "RALPHTHON" (one word, all caps).
- Make sure the lobster emoji 🦞 renders.

## Done definition

- File exists at the path above, ffprobe shows: 1080x1920, 30fps, ~5s
  duration, stereo aac audio, h264 yuv420p
- You opened the rendered mp4 by extracting frames at t=0.5, 1.5, 3.0,
  4.5 and visually verified each frame matches the spec above. If a
  frame is wrong, fix and re-render.
- Report back with: ffprobe summary, 4 frame paths you verified, and
  any caveats.

Budget: 8 minutes. If you blow past 6 minutes, simplify (drop the
scanline pulse, drop the status block animation, just render a clean
static-then-typed card).

Make it cool.

---

## What the agent did

- First attempt: pure ffmpeg drawtext with Apple Color Emoji for 🦞 >
  hung with `Monochromatic (1bpp) fonts are not supported`
- Switched to PIL > PNG sequence > ffmpeg image2 pipeline
- Pre-rendered 🦞 + ⚡ via PIL from Apple Color Emoji at 160px, scaled
  to 64x64
- Layered: typewriter prompt (0.0-0.6s) > title + subline (0.6-2.0s) >
  status block fade-in (2.0-3.5s) > hold (3.5-4.7s) > fade-to-near-black
  (4.7-5.0s)
- Verified at t=0.5, 1.5, 3.0, 4.5, 4.95 by extracting and visually
  inspecting jpgs
- Wall clock: ~5 min including the dead-end emoji attempt
