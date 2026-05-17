# Lobster repo agent prompt . meta

The prompt I fed to a coding agent to build out this very repo from
the working ralphthon project directory. The agent stalled on the
watchdog after 600s without progress (worktree was set up but no
files written yet). I switched to foreground execution and finished
the repo by hand.

Worth keeping the prompt for next time . the SCOPE is right, the
delegation was the mistake. For tightly-scoped file-creation tasks,
foreground is often faster than spawning + worktree overhead.

---

Build a clean, public-ready skills repo for making vertical
hackathon-interview reels.

## Target

- **Local path**: `~/path/to/lobster/`
- **Remote**: `git@github.com:<you>/lobster.git`
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
│   └── manifest.example.json
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
5. Pick a palette tied to the event mascot
6. Light vignette PI/5 is the default finishing move

## Constraints

- NO em dashes (U+2014) or en dashes (U+2013) anywhere
- License: MIT
- Python 3.11+
- Do NOT vendor large binaries

## Steps

1. mkdir + cd to lobster
2. Build the layout, write the scripts with argparse where appropriate
3. Write README + SKILL + docs
4. git init, commit, branch -M main, remote add, push -u origin main
5. If push fails because the repo doesn't exist yet, try
   `gh repo create sawasawasawa/lobster --public --source=. --remote=origin --push`

## Done definition

- Repo exists, push succeeded
- No em dashes anywhere (`grep -r "U+2014"` returns nothing)

Budget: 12 minutes.

---

## What happened

The agent worktree was set up but no progress files were written.
Stream watchdog killed the agent after 600s without stdout. Likely
the agent was deep in a context-loading phase reading source files
and not emitting tokens.

**Lesson**: for repo-creation tasks that are mostly file writes (not
research, not synthesis), do it in foreground. Background agents
shine on long-running compute (render, transcribe) where stalls are
diagnosable from output streams.
