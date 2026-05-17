"""Ralphthon @SG outro . 5s, 1080x1920, 30fps.

Dry terminal-style. Types a SQL query, prints redacted rows, lands the
"WHO IS GONNA WIN?" gut-punch in lobster red.

Pipeline: per-frame PIL render -> PNG sequence -> ffmpeg image2 -> mp4 (+silent AAC).
"""
from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ============================================================================
# CONFIG
# ============================================================================
OUT_DIR = Path("work/outro")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR = OUT_DIR / "_frames"
FINAL_MP4 = OUT_DIR / "outro.mp4"

W, H = 1080, 1920
FPS = 30
DURATION = 5.0
TOTAL_FRAMES = int(round(DURATION * FPS))  # 150

import os as _os
_HOME = _os.path.expanduser("~")
_JBM_CANDIDATES = [
    f"{_HOME}/Library/Fonts/JetBrainsMonoNL-Bold.ttf",
    f"{_HOME}/Library/Fonts/JetBrainsMono-Bold.ttf",
    "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
]
JBM_BOLD = next((p for p in _JBM_CANDIDATES if _os.path.exists(p)),
                "/System/Library/Fonts/Menlo.ttc")
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"

# Palette
BG = (7, 9, 12)              # #07090C deep near-black
DOT_GRID = (22, 28, 36)      # faint grid dots
GREEN = (135, 199, 107)      # #87C76B terminal green / prompt + SQL keyword
DIM = (168, 180, 194)        # #A8B4C2 result rows
LOBSTER = (217, 83, 63)      # #D9533F WHO IS GONNA WIN
SUB = (110, 122, 132)        # small grand-prize line
DOT_R = (255, 95, 86)
DOT_Y = (255, 189, 46)
DOT_G_TL = (39, 201, 63)
SHADOW = (0, 0, 0, 180)


# ============================================================================
# FONT CACHE
# ============================================================================
_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

def F(size: int, path: str = JBM_BOLD) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


_emoji_cache: dict[int, ImageFont.FreeTypeFont] = {}
EMOJI_VALID = (20, 32, 40, 48, 64, 96, 160)

def Femoji(size: int) -> ImageFont.FreeTypeFont:
    # Apple Color Emoji has fixed bitmap sizes . pick nearest valid
    pick = min(EMOJI_VALID, key=lambda s: abs(s - size))
    if pick not in _emoji_cache:
        _emoji_cache[pick] = ImageFont.truetype(EMOJI_FONT, pick)
    return _emoji_cache[pick]


# ============================================================================
# LAYOUT (vertical 1080x1920)
# ============================================================================
# Top bar with traffic lights: y=72-132
TITLE_BAR_Y = 64
TITLE_BAR_H = 76
DOTS_LEFT = 56
DOTS_Y = TITLE_BAR_Y + TITLE_BAR_H // 2
DOTS_R = 14

# SQL prompt line
SQL_FONT_SIZE = 42
SQL_Y = 340

# Result rows
ROW_FONT_SIZE = 40
ROWS_Y_START = SQL_Y + 130
ROW_GAP = 78

# WHO IS GONNA WIN big title
TITLE_FONT_SIZE = 86
TITLE_Y = 1260

# Subtitle under title
SUBTITLE_FONT_SIZE = 30
SUBTITLE_GAP = 64  # below title baseline

# Padding from left edge for terminal text
TEXT_LEFT = 90


# ============================================================================
# TEXT CONTENT
# ============================================================================
SQL_PROMPT = "> "
SQL_BODY   = "SELECT winner FROM ralphthon;"
SQL_FULL   = SQL_PROMPT + SQL_BODY  # for timing

RESULT_ROWS = [
    ("▸ result: ",   "[REDACTED]",          False),
    ("▸ chances: ",  "pending lobster ",    True),   # True = lobster emoji at end
    ("▸ judges: ",   "deliberating...",     False),
]

TITLE_TEXT = "WHO IS GONNA WIN?"
SUBTITLE_TEXT = "grand prize  ·  $10k OpenAI credits"


# ============================================================================
# TIMING (seconds)
# ============================================================================
T_FADE_IN_END = 0.6     # card fully in
T_TYPE_START  = 0.6
T_TYPE_END    = 1.8     # SQL fully typed (1.2s for ~30 chars)
T_ROWS_START  = 1.8
T_ROWS_END    = 3.2     # all 3 rows visible
T_TITLE_IN    = 3.2
T_TITLE_SETTLE= 3.7     # scale settles
T_PULSE_START = 4.5
T_FADE_OUT    = 4.8     # last 0.2s fade


# ============================================================================
# BACKGROUND (cached static asset)
# ============================================================================
def make_background() -> Image.Image:
    """Deep near-black with very faint dot grid + title bar with traffic lights."""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Very faint dot grid . every 60px, 2px dots
    for y in range(40, H, 60):
        for x in range(40, W, 60):
            draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=DOT_GRID)

    # Title bar . subtle gradient strip
    bar_top = TITLE_BAR_Y
    bar_bot = TITLE_BAR_Y + TITLE_BAR_H
    for y in range(bar_top, bar_bot):
        t = (y - bar_top) / max(1, TITLE_BAR_H)
        r = int(18 + (12 - 18) * t)
        g = int(24 + (16 - 24) * t)
        b = int(32 + (22 - 32) * t)
        draw.line([(40, y), (W - 40, y)], fill=(r, g, b))
    # Bar outline
    draw.rectangle([40, bar_top, W - 40, bar_bot], outline=(30, 38, 48), width=1)

    # Traffic-light dots
    for i, c in enumerate([DOT_R, DOT_Y, DOT_G_TL]):
        cx = DOTS_LEFT + 30 + i * 44
        draw.ellipse(
            [cx - DOTS_R, DOTS_Y - DOTS_R, cx + DOTS_R, DOTS_Y + DOTS_R],
            fill=c,
        )

    # Title-bar label
    label_font = F(26)
    label = "ralphthon · sql shell"
    bb = draw.textbbox((0, 0), label, font=label_font)
    lw = bb[2] - bb[0]
    draw.text(((W - lw) / 2, DOTS_Y - 14), label, font=label_font, fill=(120, 132, 144))

    return img


BG_CACHE: Image.Image | None = None
def get_bg() -> Image.Image:
    global BG_CACHE
    if BG_CACHE is None:
        BG_CACHE = make_background()
    return BG_CACHE


# ============================================================================
# HELPERS
# ============================================================================
def draw_text_with_shadow(draw: ImageDraw.ImageDraw, xy, text, font, fill, shadow_offset=(3, 5)):
    """Small dark drop-shadow for readability . matches default video text style."""
    sx, sy = shadow_offset
    # Render shadow on a temp layer so we can alpha it
    # For perf, just two-pass with semi-transparent black via direct draw on RGB
    # Trick: draw the shadow as near-black with reduced fill
    draw.text((xy[0] + sx, xy[1] + sy), text, font=font, fill=(0, 0, 0))
    draw.text(xy, text, font=font, fill=fill)


def cubic_ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3


def cubic_ease_in_out(t: float) -> float:
    if t < 0.5:
        return 4 * t * t * t
    p = 2 * t - 2
    return 1 + p * p * p / 2


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ============================================================================
# FRAME RENDER
# ============================================================================
def render_frame(t: float) -> Image.Image:
    """Render one frame at time t (seconds)."""
    base = get_bg().copy().convert("RGBA")

    # ---- Card fade-in (0 -> 0.6s): blend from black to full alpha ----
    if t < T_FADE_IN_END:
        k = cubic_ease_out(t / T_FADE_IN_END)
        # Composite over solid black
        black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        base.putalpha(int(255 * k))
        base = Image.alpha_composite(black, base)
    base_rgb = base.convert("RGB")

    draw = ImageDraw.Draw(base_rgb)

    # ---- SQL typing (0.6 -> 1.8s) ----
    if t >= T_TYPE_START:
        elapsed = t - T_TYPE_START
        dur = T_TYPE_END - T_TYPE_START  # 1.2s
        progress = min(1.0, elapsed / dur)
        n_chars = int(round(progress * len(SQL_FULL)))
        typed = SQL_FULL[:n_chars]

        sql_font = F(SQL_FONT_SIZE)

        # Split into prompt (green) + body (greenish, slightly different shade for keyword vibe)
        # Simplification: render whole typed string in green (matches "prompt + SQL keyword: green")
        draw_text_with_shadow(draw, (TEXT_LEFT, SQL_Y), typed, sql_font, GREEN)

        # Cursor block at end if still typing OR softly blinking after typed
        if progress < 1.0:
            # Solid cursor while typing
            bb = draw.textbbox((TEXT_LEFT, SQL_Y), typed, font=sql_font)
            cx0 = bb[2] + 6
            cy0 = SQL_Y + 4
            draw.rectangle([cx0, cy0, cx0 + 16, cy0 + SQL_FONT_SIZE - 2], fill=GREEN)
        elif t < T_TITLE_IN:
            # Blinking cursor at end of SQL line until title takes over
            blink = (math.sin((t - T_TYPE_END) * math.pi * 3) > 0)
            if blink:
                bb = draw.textbbox((TEXT_LEFT, SQL_Y), SQL_FULL, font=sql_font)
                cx0 = bb[2] + 6
                cy0 = SQL_Y + 4
                draw.rectangle([cx0, cy0, cx0 + 16, cy0 + SQL_FONT_SIZE - 2], fill=GREEN)

    # ---- Result rows (1.8 -> 3.2s) . stagger reveal ----
    if t >= T_ROWS_START:
        elapsed = t - T_ROWS_START
        rows_dur = T_ROWS_END - T_ROWS_START  # 1.4s
        per_row = rows_dur / len(RESULT_ROWS)  # ~0.467s each

        row_font = F(ROW_FONT_SIZE)

        for i, (label, val, has_lobster) in enumerate(RESULT_ROWS):
            row_start = i * per_row
            if elapsed < row_start:
                continue
            # Fade-in per row over 0.25s with slight upward slide
            local = min(1.0, (elapsed - row_start) / 0.30)
            local_eased = cubic_ease_out(local)
            alpha = int(255 * local_eased)
            slide_y = int((1 - local_eased) * 12)

            y = ROWS_Y_START + i * ROW_GAP + slide_y

            # Render row to a temp layer for alpha
            row_layer = Image.new("RGBA", (W, ROW_FONT_SIZE + 30), (0, 0, 0, 0))
            rd = ImageDraw.Draw(row_layer)

            # Shadow + label
            rd.text((TEXT_LEFT + 3, 5 + 5), label, font=row_font, fill=(0, 0, 0, alpha))
            rd.text((TEXT_LEFT, 5),     label, font=row_font, fill=(*GREEN, alpha))

            # Value (dim)
            lb = rd.textbbox((TEXT_LEFT, 5), label, font=row_font)
            vx = lb[2] + 4
            rd.text((vx + 3, 5 + 5), val, font=row_font, fill=(0, 0, 0, alpha))
            rd.text((vx, 5),         val, font=row_font, fill=(*DIM, alpha))

            # Lobster emoji inline at end of "pending lobster "
            if has_lobster:
                vb = rd.textbbox((vx, 5), val, font=row_font)
                ex = vb[2] + 2
                ey = 5 - 4  # nudge emoji up to align baseline-ish

                emoji_font = Femoji(ROW_FONT_SIZE + 8)  # slightly larger to read
                # Apple Color Emoji renders only via embedded_color=True onto an RGBA layer
                em_layer = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
                em_draw = ImageDraw.Draw(em_layer)
                em_draw.text((0, 0), "🦞", font=emoji_font, embedded_color=True)
                # Apply alpha for fade-in
                if alpha < 255:
                    a = em_layer.split()[3].point(lambda p: int(p * alpha / 255))
                    em_layer.putalpha(a)
                row_layer.alpha_composite(em_layer, (ex, ey))

            base_rgba = base_rgb.convert("RGBA")
            base_rgba.alpha_composite(row_layer, (0, y))
            base_rgb = base_rgba.convert("RGB")
            draw = ImageDraw.Draw(base_rgb)

    # ---- Big "WHO IS GONNA WIN?" title (3.2 -> 4.5s arrival, hold to end) ----
    if t >= T_TITLE_IN:
        elapsed = t - T_TITLE_IN
        # Scale-up + fade-in over 0.5s with overshoot
        intro_dur = T_TITLE_SETTLE - T_TITLE_IN  # 0.5s
        k = min(1.0, elapsed / intro_dur)
        k_eased = cubic_ease_out(k)
        scale = lerp(0.86, 1.0, k_eased)
        alpha = int(255 * k_eased)

        # Pulse during last 0.5s (4.5 -> 5.0)
        pulse_scale = 1.0
        if t >= T_PULSE_START:
            p = (t - T_PULSE_START) / max(0.001, (DURATION - T_PULSE_START))
            # subtle breathe: 1.0 -> 1.025 -> 1.0
            pulse_scale = 1.0 + 0.025 * math.sin(p * math.pi)

        final_scale = scale * pulse_scale

        # Render title at base size into RGBA, then resize and paste
        title_font = F(TITLE_FONT_SIZE)
        # Measure to size a tight canvas
        bb = title_font.getbbox(TITLE_TEXT)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        pad = 40
        title_layer = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
        tdraw = ImageDraw.Draw(title_layer)
        # Drop shadow
        tdraw.text((pad - bb[0] + 5, pad - bb[1] + 7), TITLE_TEXT, font=title_font, fill=(0, 0, 0, alpha))
        # Main fill in lobster red
        tdraw.text((pad - bb[0], pad - bb[1]), TITLE_TEXT, font=title_font, fill=(*LOBSTER, alpha))

        # Apply scale
        if abs(final_scale - 1.0) > 0.001:
            new_w = max(1, int(title_layer.width * final_scale))
            new_h = max(1, int(title_layer.height * final_scale))
            title_layer = title_layer.resize((new_w, new_h), Image.LANCZOS)

        tx = (W - title_layer.width) // 2
        ty = TITLE_Y - title_layer.height // 2

        base_rgba = base_rgb.convert("RGBA")
        base_rgba.alpha_composite(title_layer, (tx, ty))
        base_rgb = base_rgba.convert("RGB")
        draw = ImageDraw.Draw(base_rgb)

        # ---- Subtitle (grand prize) . fades in slightly after title ----
        sub_alpha_t = max(0.0, min(1.0, (elapsed - 0.2) / 0.4))
        if sub_alpha_t > 0:
            sub_alpha = int(255 * cubic_ease_out(sub_alpha_t))
            sub_font = F(SUBTITLE_FONT_SIZE)
            sb = sub_font.getbbox(SUBTITLE_TEXT)
            sw = sb[2] - sb[0]
            sh = sb[3] - sb[1]
            sub_layer = Image.new("RGBA", (sw + 20, sh + 20), (0, 0, 0, 0))
            sdraw = ImageDraw.Draw(sub_layer)
            sdraw.text((10 - sb[0] + 2, 10 - sb[1] + 3), SUBTITLE_TEXT, font=sub_font, fill=(0, 0, 0, sub_alpha))
            sdraw.text((10 - sb[0], 10 - sb[1]), SUBTITLE_TEXT, font=sub_font, fill=(*SUB, sub_alpha))

            sx = (W - sub_layer.width) // 2
            sy = TITLE_Y + int((TITLE_FONT_SIZE * final_scale) / 2) + 30
            base_rgba2 = base_rgb.convert("RGBA")
            base_rgba2.alpha_composite(sub_layer, (sx, sy))
            base_rgb = base_rgba2.convert("RGB")

    # ---- Soft fade-out at very end (4.8 -> 5.0s) ----
    if t >= T_FADE_OUT:
        k = min(1.0, (t - T_FADE_OUT) / (DURATION - T_FADE_OUT))
        # Fade toward black
        black = Image.new("RGB", (W, H), (0, 0, 0))
        base_rgb = Image.blend(base_rgb, black, k * 0.7)

    return base_rgb


# ============================================================================
# MAIN
# ============================================================================
def main():
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    # Clean any prior frames
    for p in FRAMES_DIR.glob("*.png"):
        p.unlink()

    print(f"[render] frames -> {FRAMES_DIR}")
    for i in range(TOTAL_FRAMES):
        t = i / FPS
        img = render_frame(t)
        out = FRAMES_DIR / f"frame_{i:04d}.png"
        img.save(out, "PNG", optimize=False, compress_level=1)
        if i % 30 == 0:
            print(f"  frame {i}/{TOTAL_FRAMES} t={t:.2f}s")
    print(f"[render] done . {TOTAL_FRAMES} frames")

    # ffmpeg: PNG seq + silent stereo AAC -> mp4 h264 yuv420p +faststart
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES_DIR / "frame_%04d.png"),
        "-f", "lavfi",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t", f"{DURATION:.3f}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "slow",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-shortest",
        "-movflags", "+faststart",
        str(FINAL_MP4),
    ]
    print("[ffmpeg]", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"[done] -> {FINAL_MP4}")


if __name__ == "__main__":
    main()
