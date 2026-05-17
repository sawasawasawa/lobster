# lobster

> Ralphthon @SG 2026 submission. An AI-agent pipeline that turns 9 builder
> phone interviews into a 69-second vertical highlight reel with
> terminal-style typewriter captions, on the lobster's hour-and-change
> timetable.

This repo IS the submission. The pitch: I didn't code an app at Ralphthon.
I ran agents that built a video pipeline that interviewed nine other
builders and produced a publishable highlight reel. The agents wrote
their own scripts, generated their own intro / outro cards, and pushed
their own GitHub repos. I was the editor with veto power and a
TaskCreate habit.

The reel is at
[`watchns.world`-flavored social channels](https://watchns.world)
(separately). This repo is the blueprint: every script, every agent
prompt, every gotcha that cost an hour the first time.

## What's here

```
lobster/
├── README.md                  # you are here
├── SKILL.md                   # claude-code skill spec (for skill loader)
├── LICENSE                    # MIT
├── requirements.txt           # python deps
├── scripts/
│   ├── transcribe.py             # faster-whisper medium.en, parallel
│   ├── cut_clip.py               # plain ffmpeg cut, no silenceremove (sync bug)
│   ├── overlay_one_cut.py        # per-cut driver for the AA-style overlay
│   ├── overlay_terminal.py       # cv2 per-frame composite, vendored from AA skill
│   ├── render_intro.py           # PIL -> PNG sequence -> ffmpeg, RALPHTHON intro
│   ├── render_outro.py           # PIL -> PNG sequence -> ffmpeg, "WHO IS GONNA WIN?"
│   └── concat_reel.py            # filter_complex concat with apad/atrim
├── prompts/
│   ├── intro_agent.md            # actual prompt fed to the Engineer agent
│   ├── outro_agent.md            # actual prompt fed to the Engineer agent
│   └── lobster_repo_agent.md     # actual prompt that built (some of) this repo
├── examples/
│   └── ralphthon-2026-manifest.json   # 8-speaker punchline manifest (v2)
├── docs/
│   ├── pipeline.md               # end-to-end stage diagram + rationale
│   └── gotchas.md                # the lessons that cost me the most time
└── assets/
    ├── intro/                    # placeholder; intros are generated, not vendored
    └── outro/                    # placeholder; outros are generated, not vendored
```

## The pipeline in one paragraph

`transcribe.py` runs faster-whisper medium.en on each source MOV with
word timestamps, parallel up to 3 workers. A human picks `t_in / t_out`
windows per speaker and writes a JSON manifest. `cut_clip.py` does a
single-pass ffmpeg per-clip: rotate (auto), scale to 1080x1920, mild
color grade, loudnorm to -16 LUFS / -3 dBTP. `overlay_one_cut.py` slices
the source word-timestamps to the cut window, writes a YAML config, and
invokes `overlay_terminal.py` (cv2 per-frame composite) to add the
top-left agent toast and the bottom terminal-window subtitle panel with
per-word reveal. `render_intro.py` and `render_outro.py` build the event
intro and "WHO IS GONNA WIN?" outro cards by rendering 150 PIL frames
each and piping to ffmpeg. `concat_reel.py` filter-complexes everything
together with `apad,atrim=duration=X` per segment, adds `vignette=PI/5`,
runs a final `loudnorm` pass, and writes a single mp4. Total wall clock
on the Ralphthon submission: under 20 minutes from raw phone vids to
final reel, most of it the cv2 overlay step (cacheable, parallelizable).

## Skills + agents used

What was actually invoked during this hackathon:

- **PAI Algorithm v3.5.0** . Mateusz's personal AI infrastructure;
  enforces 7-phase OBSERVE → THINK → PLAN → BUILD → EXECUTE → VERIFY →
  LEARN with atomic ISC criteria gates and TaskCreate tracking.
- **`agents-anonymous-video` Claude Code skill** . internal AA × NS
  event reel skill from `~/.claude/skills/` ;
  vendored `overlay_terminal.py` from it. See credit below.
- **2 background Engineer agents** . one rendered the intro card, one
  rendered the outro card. Both produced clean mp4s in under 5 minutes
  from their full prompts (see `prompts/`).
- **faster-whisper** (medium.en, int8 on CPU) . 3 parallel workers for
  source transcription; ~30s per 30s of audio on M-series Macs.
- **ffmpeg 8.0** . every encode, decode, concat, vignette, loudnorm pass.
- **JetBrains Mono Bold + Regular** . only font in the terminal panel +
  toast. Apple Color Emoji for the lobster, pre-rendered via PIL (NOT
  drawtext, see `docs/gotchas.md`).

## Reproducing it

```bash
git clone https://github.com/sawasawasawa/lobster.git
cd lobster
pip install -r requirements.txt

# 1. Transcribe
python3 scripts/transcribe.py --srcs path/to/IMG_*.MOV --out work/transcripts/

# 2. Pick punchlines manually, write manifest.json (see examples/)

# 3. Cut + overlay per speaker (loop over manifest)
python3 scripts/cut_clip.py --src ... --in 1.85 --out 8.30 --idx 01 ...
python3 scripts/overlay_one_cut.py --cut ... --name "Dan" --topic "..." ...

# 4. Generate intro + outro (parameterize event name in the renderers)
python3 scripts/render_intro.py --event-name RALPHTHON --venue "@ SG" ...
python3 scripts/render_outro.py --prize "grand prize . \$10k OpenAI credits" ...

# 5. Concat
python3 scripts/concat_reel.py --intro ... --outro ... --cuts-dir work/cuts_overlaid/
```

A one-shot driver `scripts/run_pipeline.py` is on the to-do (the
hackathon clock ran out on it). PRs welcome.

## The Ralphthon submission specifically

The reel: 69.24s vertical 1080x1920, 9 speakers, terminal-style captions,
shipped on the day of the event. Speakers (in order):

1. **Dan** . agentic Rube Goldberg across phones
2. **Luke Hubbard** . Mirrorbase . data sovereignty for AI chats
3. **Mayank** . skill to make web apps AI-ready
4. **Pushkar** . MCP tools to accelerate research (NTU)
5. **Mervin** . AI dashboard for customer-service chats
6. **Arun** . reviewer agent that keeps agents on track
7. **Nachika Freddy** . Lumina . AI SaaS for dev teams
8. **Stéphane** . better AMM for prediction markets
9. **Alin** . SEO check + ranking improver

Intro: "RALPHTHON @ SG . supported by OpenAI" terminal init card with
status block + lobster.
Outro: dry-irony SQL shell, `SELECT winner FROM ralphthon;`,
`▸ chances: pending lobster 🦞`, big lobster-red "WHO IS GONNA WIN?"
headline.

## Credits

- `scripts/overlay_terminal.py` is vendored from the internal
  `agents-anonymous-video` skill, originally built for the
  Agents Anonymous × Network School event reels. AA itself is a riff on
  [@steipete's Claude Code Anonymous](https://x.com/steipete). Format
  credit where credit is due.
- Ralphthon @SG supported by OpenAI. Hosted by Team Attention + Hashed.
  Lobster mascot is theirs, used affectionately.
- Network School (NS) . the community that runs the AA × NS event reels.
- Claude Code + the PAI personal-AI-infrastructure framework . the
  agents and the 7-phase algorithm that orchestrated this.

## License

MIT . see `LICENSE`.
