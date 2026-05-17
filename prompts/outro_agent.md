# Outro agent prompt . Ralphthon 2026

Verbatim prompt fed to a coding agent to generate the 5-second
`outro.mp4`. The agent ran in a worktree, completed in ~4.5 minutes,
produced 1080x1920 30fps mp4 at 213 KB.

Reuse pattern: change the prize line, the headline question, the event
name in the title bar. Keep everything else.

---

You are generating a 5-second outro mp4 for a hackathon highlight reel.
NO QUESTIONS . execute. Write the final file to:

`<absolute_path>/work/outro/outro.mp4`

## Hard specs

- Resolution: **1080x1920 vertical**
- Duration: 5.0s exactly
- fps: 30
- Codec: libx264 -pix_fmt yuv420p -crf 18 -preset slow
- Audio: silent stereo AAC 44.1kHz 192k
- Container: .mp4 with `+faststart`

## Event context

- **Ralphthon @SG supported by OpenAI** (Singapore, today)
- Hosted by Team Attention + Hashed
- Lobster mascot . emoji 🦞 is on-brand
- AI hackathon
- Grand Prize: $10k OpenAI API credits, 6 months ChatGPT Pro, $3k NS
  credits

## Intent

The video ends. We just met 6 builders and saw the essence of what
they're building. The outro asks the question every viewer is now
thinking: **WHO IS GONNA WIN?**

Dry terminal-style irony (NOT shouty hype, NOT wholesome earnest).
Picture: a terminal in the void, a single prompt, a typed-out question,
then a `[REDACTED]` punchline.

## Card progression (5.0s timeline)

- t=0.0-0.6s . fade in dark terminal card: title bar with 3 traffic-
  light dots (red/yellow/green) top-left, terminal body below
- t=0.6-1.8s . type out (per-char reveal at ~30ms/char):
  `> SELECT winner FROM ralphthon;`
- t=1.8-3.2s . output rolls in below the SQL:
  ```
  ▸ result: [REDACTED]
  ▸ chances: pending lobster 🦞
  ▸ judges: deliberating...
  ```
- t=3.2-4.5s . big bottom-centered terminal title appears (slight
  scale-up): `WHO IS GONNA WIN?` and a small line under it:
  `grand prize . $10k OpenAI credits`
- t=4.5-5.0s . hold, soft pulse on the question, light 0.3s fade-out
  at very end

## Palette

- Background: deep near-black `#07090C` with very faint dot-grid
- `>_` prompt + SQL keyword: terminal green `#87C76B`
- Result rows: dim white `#A8B4C2`
- "WHO IS GONNA WIN?" big text: lobster red `#D9533F`
- Traffic-light dots: red `#FF5F56`, yellow `#FFBD2E`, green `#27C93F`
- NEVER pure black

## Tools . your choice

PIL > PNG sequence > ffmpeg image2 > mp4 is recommended for typography
+ emoji control.

## Constraints

- NO em dashes (U+2014) or en dashes (U+2013).
- "WHO IS GONNA WIN?" . exact text, all caps, with the question mark.
- Lobster emoji 🦞 must render visibly.

## Done definition

- File exists, ffprobe shows: 1080x1920, 30fps, ~5s, stereo aac, h264
  yuv420p
- Extract frames at t=0.5, 1.5, 2.8, 4.0, 4.8 and Read each jpg to
  visually verify
- Report: ffprobe summary, frame paths verified, any caveats

Budget: 8 minutes.

Make it dry and funny.

---

## What the agent did

- Chose per-frame PIL render over chained ffmpeg drawtext for the
  typing animation + row stagger + headline scale-up
- Caught a hidden em dash in the title bar text on first verification
  pass (`ralphthon . sql shell`) and replaced with U+00B7 middle dot
  (`ralphthon · sql shell`) per the global no-em-dashes rule
- Re-verified at t=0.5, 1.5, 2.8, 4.0, 4.8
- Wall clock: ~4.5 min
