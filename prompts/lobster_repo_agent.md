# Lobster repo agent prompt . meta

The prompt I fed to a Claude Code Engineer agent to extract this very
repo from the Ralphthon project working directory. The agent stalled
on the watchdog after 600s without progress (worktree was set up but
no files written yet). I switched to foreground execution and finished
the repo by hand.

Worth keeping the prompt for next time . the SCOPE is right, the
delegation was the mistake. For tightly-scoped file-creation tasks,
foreground is often faster than spawning + worktree overhead.

---

Build a clean, public-ready skills repo for making AA-style vertical
hackathon-interview reels. Source-of-truth pipeline lives in:

`/Users/mateuszsawka/Projects/priv/ai/ns/video-edits/projects/ralphthon-hackathon/`

That project just shipped its v3 reel (69s vertical, 9 speakers, AA003-
style terminal subtitles + agent toasts, generated intro/outro). The
user wants this pipeline distilled into a standalone repo so it's
reusable for the NEXT event.

## Target

- **Local path**: `/Users/mateuszsawka/Projects/priv/ai/lobster/`
- **Remote**: `git@github.com:sawasawasawa/lobster.git`
- **Branch**: `main`

## Suggested repo layout

```
lobster/
├── README.md
├── SKILL.md
├── requirements.txt
├── scripts/
│   ├── transcribe.py
│   ├── cut_clip.py
│   ├── overlay_one_cut.py
│   ├── concat_reel.py
│   ├── overlay_terminal.py
│   ├── render_intro.py
│   └── render_outro.py
├── examples/
│   └── manifest.example.yaml
├── docs/
│   ├── pipeline.md
│   └── gotchas.md
└── prompts/
    ├── intro_agent.md
    ├── outro_agent.md
    └── lobster_repo_agent.md
```

## Critical content to capture in docs/gotchas.md

1. `silenceremove` desyncs A/V in talking-head cuts
2. Apple Color Emoji + ffmpeg drawtext is a dead end
3. AAC concat AV drift over N segments
4. iPhone portrait sources: no blur-pad, ever
5. AA × NS branding TRUTH: palette + provenance
6. Light vignette PI/5 is the default finishing move

## Constraints

- NO em dashes (U+2014) or en dashes (U+2013) anywhere
- Credit the AA skill in README.md
- License: MIT
- Python 3.11+
- Do NOT vendor large binaries

## Steps

1. mkdir + cd to lobster
2. Build the layout, adapt the scripts (don't copy verbatim, clean them)
3. Write README + SKILL + docs
4. git init, commit, branch -M main, remote add, push -u origin main
5. If push fails, try `gh repo create sawasawasawa/lobster --public
   --source=. --remote=origin --push`

## Done definition

- Repo exists, push succeeded
- No em dashes anywhere (`grep -r "."` returns nothing)

Budget: 12 minutes.

---

## What happened

Agent worktree was set up at
`/Users/mateuszsawka/Projects/priv/ai/ns/video-edits/.claude/worktrees/agent-a3b2b0d3ee611cbea/`
but no progress files were written. Stream watchdog killed the agent
after 600s without stdout. Likely the agent was deep in a context-loading
phase reading source files and not emitting tokens.

**Lesson**: for repo-creation tasks that are mostly file writes (not
research, not synthesis), do it in foreground. Background agents shine
on long-running compute (render, transcribe) where stalls are
diagnosable from output streams.
