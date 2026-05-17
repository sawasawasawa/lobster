#!/usr/bin/env python3
"""
Ralphthon hackathon . 5s vertical intro (1080x1920 / 30fps).

Evokes AA × NS terminal aesthetic with a NEW Ralphthon palette
(deep near-black bg, prompt green, lobster red title).
"""
import subprocess, shlex, sys, os, pathlib

OUT_DIR = pathlib.Path(__file__).parent
OUT = OUT_DIR / "intro.mp4"

# -------- assets --------
FONT_MONO = "/Users/mateuszsawka/Library/Fonts/JetBrainsMonoNL-Bold.ttf"
FONT_EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"
if not os.path.exists(FONT_MONO):
    FONT_MONO = "/System/Library/Fonts/Menlo.ttc"

# -------- palette --------
BG       = "0x07090C"      # background fill
PROMPT   = "0x87C76B"       # >_ prompt green
TITLE    = "0xD9533F"       # Ralphthon lobster red
SUBLINE  = "0xA8B3C0"       # cool grey for subline
WHITE    = "0xE8EEF5"       # cool white
DIM      = "0x4A5260"       # status block label dim
GREENDIM = "0x4F7A3F"       # dimmer green for cursor blink fade
DOTRED   = "0xFF5F57"       # mac dot red
DOTAMBER = "0xFEBC2E"       # mac dot amber
DOTGREEN = "0x28C840"       # mac dot green

W, H, FPS, DUR = 1080, 1920, 30, 5.0

# -------- text content --------
PROMPT_TEXT = "> init ralphthon..."   # types in 0.0-0.6s
TITLE_TEXT  = "RALPHTHON"             # 0.6-2.0s
SUB_TEXT    = "@ SG  .  supported by OpenAI"   # use literal ' . ' separators
STATUS_LINES = [
    ("status:",   "6 builders interviewed"),
    ("location:", "suntec t1 . level 33"),
    ("vibe:",     "lobster-coded"),  # emoji rendered as separate layer
]

# -------- helper: escape for drawtext text= field --------
def esc(s):
    # Order matters: backslash first
    return (s.replace("\\", "\\\\")
             .replace(":", "\\:")
             .replace("'", "’")   # we strip later for fonts that lack apostrophe; here just avoid single-quote in shell
             .replace(",", "\\,")
             .replace("%", "\\%"))

# We will pass the whole filter graph via a -filter_complex_script file to avoid
# shell quoting nightmares.

filters = []

# 1) base background (solid fill, 5s, 30fps, 1080x1920)
filters.append(
    f"color=c={BG}:s={W}x{H}:r={FPS}:d={DUR},format=yuv420p[bg]"
)

# 2) faint horizontal hairline under the prompt (subtle terminal divider)
#    drawn as a 2-px dim line at y=210 with low alpha via drawbox over the bg.
#    We'll chain everything as drawbox/drawtext over [bg].

chain_in = "bg"
chain_out_idx = 0
def next_lbl():
    global chain_out_idx
    chain_out_idx += 1
    return f"v{chain_out_idx}"

def add(filter_expr):
    """Append a filter that consumes the running chain and outputs the next label."""
    global chain_in
    lbl_out = next_lbl()
    filters.append(f"[{chain_in}]{filter_expr}[{lbl_out}]")
    chain_in = lbl_out

# --- mac traffic light dots (top-left), always visible ---
# red, amber, green dots at top-left
add(f"drawbox=x=46:y=46:w=22:h=22:color={DOTRED}@1.0:t=fill")
add(f"drawbox=x=84:y=46:w=22:h=22:color={DOTAMBER}@1.0:t=fill")
add(f"drawbox=x=122:y=46:w=22:h=22:color={DOTGREEN}@1.0:t=fill")

# --- faint hairline divider under prompt area (y ~ 250) ---
add(f"drawbox=x=40:y=260:w={W-80}:h=1:color=0x1F2A38@1.0:t=fill")

# --- faint horizontal scanlines (very subtle, static) across whole frame ---
# 4 thin dim lines spaced through frame for texture
for y in (520, 1050, 1450, 1750):
    add(f"drawbox=x=0:y={y}:w={W}:h=1:color=0x10161E@1.0:t=fill")

# --- prompt typewriter (0.0-0.6s) ---
# Reveal one chunk at a time. Full string: "> init ralphthon..."
# Total 19 chars. 5 stages over 0.6s -> step every 0.12s.
prompt_full = PROMPT_TEXT
stages = [
    (0.00, 0.12, "> "),
    (0.12, 0.24, "> in"),
    (0.24, 0.36, "> init "),
    (0.36, 0.48, "> init ral"),
    (0.48, 0.58, "> init ralphtho"),
    (0.58, 5.00, "> init ralphthon..."),
]
for (t0, t1, text) in stages:
    enable = f"between(t,{t0},{t1})"
    txt = esc(text)
    add(
        f"drawtext=fontfile='{FONT_MONO}':text='{txt}':"
        f"fontcolor={PROMPT}:fontsize=42:x=44:y=210:"
        f"shadowcolor=0x000000@0.6:shadowx=0:shadowy=0:"
        f"enable='{enable}'"
    )

# --- blinking cursor block right after the prompt (visible 0.0-0.6s while typing) ---
# Use drawbox with enable expression that toggles on every 0.25s.
# Active windows: [0.00,0.20], [0.40,0.55]
add(
    f"drawbox=x=300:y=210:w=20:h=44:color={PROMPT}@1.0:t=fill:"
    f"enable='between(t,0.00,0.18)+between(t,0.36,0.52)'"
)

# --- RALPHTHON big title (0.6-5.0s) with fade-in 0.6-1.0s ---
# Centered. Font size 168 in JetBrains Mono Bold; total chars 9 -> width ~9*100=900 < 1080 ok.
# Use alpha fade via fontcolor alpha expression isn't supported per-frame in drawtext;
# instead, stack 2 drawtext layers: one with low alpha until 1.0s, then full. Simpler:
# do progressive reveal by enabling at 0.6s, with subtle glow underneath.
# Glow: draw the title 3 times with darker red at slight offsets for blur-feel.
# Title vertical position: roughly center upper-third, y ~ 760
TITLE_Y = 720
TITLE_FONTSIZE = 168
title_txt = esc(TITLE_TEXT)

# Glow layers (offset blurry feel) - drawn first underneath
for dx, dy, alpha in [(-3,-3,0.35),(3,3,0.35),(0,-5,0.35),(0,5,0.35),(-6,0,0.25),(6,0,0.25)]:
    add(
        f"drawtext=fontfile='{FONT_MONO}':text='{title_txt}':"
        f"fontcolor={TITLE}@{alpha}:fontsize={TITLE_FONTSIZE}:"
        f"x=(w-text_w)/2+{dx}:y={TITLE_Y}+{dy}:"
        f"enable='gte(t,0.6)'"
    )

# Main title (sharp, on top of glow)
add(
    f"drawtext=fontfile='{FONT_MONO}':text='{title_txt}':"
    f"fontcolor={TITLE}:fontsize={TITLE_FONTSIZE}:"
    f"x=(w-text_w)/2:y={TITLE_Y}:"
    f"shadowcolor=0x000000@0.7:shadowx=0:shadowy=6:"
    f"enable='gte(t,0.6)'"
)

# --- subline (1.0-5.0s) ---
# We avoid emoji and special separators; use dot-with-spaces ' . '
sub_txt = esc(SUB_TEXT)
add(
    f"drawtext=fontfile='{FONT_MONO}':text='{sub_txt}':"
    f"fontcolor={SUBLINE}:fontsize=38:"
    f"x=(w-text_w)/2:y={TITLE_Y + TITLE_FONTSIZE + 80}:"
    f"enable='gte(t,1.0)'"
)

# --- divider under subline ---
add(
    f"drawbox=x=(w-360)/2:y={TITLE_Y + TITLE_FONTSIZE + 160}:w=360:h=1:"
    f"color=0x2A3340@1.0:t=fill:enable='gte(t,1.2)'"
)

# --- status block (2.0-5.0s) ---
# Three lines, staggered: 2.0s, 2.3s, 2.6s
STATUS_X = 80
STATUS_Y = 1300
LINE_GAP = 80
status_font = 36
label_font = 36
hash_font = 36

# Use # as block bullet (works in JetBrains Mono); render bullet in DIM color
for i, (label, value) in enumerate(STATUS_LINES):
    appear = 2.0 + 0.3 * i
    y = STATUS_Y + i * LINE_GAP
    # bullet
    add(
        f"drawtext=fontfile='{FONT_MONO}':text='#':"
        f"fontcolor={DIM}:fontsize={hash_font}:"
        f"x={STATUS_X}:y={y}:"
        f"enable='gte(t,{appear})'"
    )
    # label (e.g. "status:") in white
    label_esc = esc(label)
    add(
        f"drawtext=fontfile='{FONT_MONO}':text='{label_esc}':"
        f"fontcolor={WHITE}:fontsize={label_font}:"
        f"x={STATUS_X + 50}:y={y}:"
        f"enable='gte(t,{appear})'"
    )
    # value in prompt-green
    value_esc = esc(value)
    add(
        f"drawtext=fontfile='{FONT_MONO}':text='{value_esc}':"
        f"fontcolor={PROMPT}:fontsize={status_font}:"
        f"x={STATUS_X + 270}:y={y}:"
        f"enable='gte(t,{appear})'"
    )

# --- emoji positions for later overlay composition ---
# Apple Color Emoji is color bitmap (sbix) and ffmpeg drawtext can't render it.
# We pre-render them to PNG via PIL (see emoji_lobster.png / emoji_zap.png) and
# composite via overlay filter, BEFORE the final fade so they fade out with the rest.
vibe_appear = 2.0 + 0.3 * 2
vibe_y = STATUS_Y + 2 * LINE_GAP
emoji_x = STATUS_X + 270 + 300
ZAP_X = emoji_x
ZAP_Y = vibe_y - 16
LOB_X = emoji_x + 70
LOB_Y = vibe_y - 16
ZAP_APPEAR = vibe_appear + 0.2
LOB_APPEAR = vibe_appear + 0.35

# Inputs: 0 = anullsrc audio, 1 = zap.png, 2 = lobster.png
# We add overlay filters using those inputs.
# Need to feed the running chain into overlay.
zap_lbl = next_lbl()
filters.append(f"[1:v]format=rgba[zap_src]")
filters.append(
    f"[{chain_in}][zap_src]overlay=x={ZAP_X}:y={ZAP_Y}:"
    f"enable='gte(t,{ZAP_APPEAR})'[{zap_lbl}]"
)
chain_in = zap_lbl

lob_lbl = next_lbl()
filters.append(f"[2:v]format=rgba[lob_src]")
filters.append(
    f"[{chain_in}][lob_src]overlay=x={LOB_X}:y={LOB_Y}:"
    f"enable='gte(t,{LOB_APPEAR})'[{lob_lbl}]"
)
chain_in = lob_lbl

# --- final fade-to-near-black 4.7-5.0s ---
add(f"fade=t=out:st=4.7:d=0.3:color=0x07090C")

# Final label rename to [vout]
filters[-1] = filters[-1].rsplit("[", 1)[0] + "[vout]"

# -------- build filter graph file --------
graph = ";\n".join(filters) + ";\n" + \
        f"anullsrc=channel_layout=stereo:sample_rate=44100[a]"

graph_path = OUT_DIR / "filter_graph.txt"
graph_path.write_text(graph)

# -------- run ffmpeg --------
cmd = [
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
    "-i", str(OUT_DIR / "emoji_zap.png"),
    "-i", str(OUT_DIR / "emoji_lobster.png"),
    "-filter_complex_script", str(graph_path),
    "-map", "[vout]", "-map", "0:a",
    "-t", f"{DUR}",
    "-r", str(FPS),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
    "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
    "-movflags", "+faststart",
    str(OUT),
]
# anullsrc is consumed separately; we need to NOT also reference it in the filter graph
# so strip the audio part from graph file (it was decorative). Rewrite:
graph_v_only = ";\n".join(filters)
graph_path.write_text(graph_v_only)

print("Running:", " ".join(shlex.quote(c) for c in cmd))
r = subprocess.run(cmd)
sys.exit(r.returncode)
