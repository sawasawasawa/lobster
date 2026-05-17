#!/usr/bin/env python3
"""Composite terminal-style agent toasts + per-word subtitle panel onto a video.

INPUT
  . A video (a plain cut, e.g. work/cuts_plain/c_01.mp4)
  . A YAML config describing the toasts (per-speaker name+topic+t_start) and
    the subtitle clips (whisper word-timestamp JSON path + clip's [v_start,
    v_end] in the input timeline, or an `override_text` for non-transcribed
    segments)

OUTPUT
  . A new video with:
    . Top-left agent toast: yellow border-left, terminal close-X, rounded
      corners, slide-in (0.45s) / hold (5s) / slide-out (0.45s)
    . Bottom terminal-window subtitle panel: 3 traffic-light dots, ">_ "
      green prompt, JetBrains Mono Bold green text, fixed full-width panel,
      blinking cursor, per-word reveal synced to whisper timestamps,
      filler words ("like") filtered out

USAGE
  python3 overlay_terminal.py path/to/config.yaml

CONFIG SCHEMA
  input:        path to source video
  output:       path to write the composite video
  fixed_panel_w: 1020            # full-width subtitle panel (vertical 1080)
  toast_top_margin: 110          # px from top edge for the toast strip
  sub_bottom_margin: 220         # px from bottom edge for the subtitle strip
  toasts:
    . slug: 01
      label: "> DAN"             # yellow line in toast
      topic: "agentic Rube Goldberg across phones"   # dim line below
      t_start: 0.20
  subtitles:
    . words_json: work/words/c_01.json   # faster-whisper word_timestamps output
      v_start: 0.000
      v_end:   6.450
    . override_text: "so I think things are changing here."
      v_start: 13.909
      v_end:   15.679
  drop_words: [like, Like, um, Um]
  patches:                       # whisper artifact fixes
    cloud: Claude

NOTES
  . Audio is byte-copied from the input (no re-encode).
  . cv2 per-frame composite. We tried ffmpeg `-loop 1 -i toast.png` chained
    overlays and it produced a runaway encode (hours of CPU, multi-GB output).
    Per-frame composite is fast (caches by (phrase_idx, n_visible, cursor_on))
    and predictable.
  . Word-by-word reveal is synced to whisper word.start times shifted by the
    clip's v_start.
  . Subtitle panel width is FIXED across phrases so it doesn't jump.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import yaml
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---- Style constants (override via YAML if you need to tweak) ----
PANEL_W, PANEL_H = 520, 120
BORDER_W = 5
PAD_X, PAD_Y = 22, 18
LINE1_SIZE, LINE2_SIZE = 30, 20
LINE_GAP = 12
YELLOW = (255, 220, 50, 255)
GREEN  = (90, 230, 130, 255)
PANEL_BG_A = 200

SLIDE_IN, HOLD, SLIDE_OUT = 0.45, 5.00, 0.45
LEFT_MARGIN = 30
FPS = 30

TOAST_CORNER_R = 12
TOAST_X_DIM = (180, 180, 200, 200)
TOAST_X_SIZE = 14
TOAST_X_MARGIN = 14

SUB_FONT_SIZE = 34
SUB_PAD_X = 32
SUB_PAD_BODY_TOP = 14
SUB_PAD_BODY_BOTTOM = 28
SUB_HEADER_H = 36
SUB_CORNER_R = 14

GREEN_BRIGHT = (140, 240, 160, 255)
PROMPT_PREFIX = '>_ '
DOT_R = 7
DOT_GAP = 22
DOT_LEFT = 22
DOT_RED    = (255, 95, 86,  255)
DOT_YELLOW = (255, 189, 46, 255)
DOT_GREEN  = (39, 201, 63,  255)
PANEL_BG  = (16, 20, 28, 220)
HEADER_BG = (10, 12, 18, 230)

# Fonts. Override via env LOBSTER_FONT_BOLD / LOBSTER_FONT_REG.
# Defaults try common macOS paths then fall back to Menlo (always present).
import os as _os
def _font_path(env_var, candidates, fallback):
    p = _os.environ.get(env_var)
    if p and _os.path.exists(p):
        return p
    for c in candidates:
        if _os.path.exists(c):
            return c
    return fallback

_HOME = _os.path.expanduser("~")
JBM_BOLD = _font_path(
    "LOBSTER_FONT_BOLD",
    [f"{_HOME}/Library/Fonts/JetBrainsMono-Bold.ttf",
     f"{_HOME}/Library/Fonts/JetBrainsMonoNL-Bold.ttf",
     "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"],
    "/System/Library/Fonts/Menlo.ttc",
)
JBM_REG = _font_path(
    "LOBSTER_FONT_REG",
    [f"{_HOME}/Library/Fonts/JetBrainsMono-Regular.ttf",
     f"{_HOME}/Library/Fonts/JetBrainsMonoNL-Medium.ttf",
     "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf"],
    "/System/Library/Fonts/Menlo.ttc",
)

# ---- Helpers ----
_font_cache = {}
def get_font(size, bold=True):
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(JBM_BOLD if bold else JBM_REG, size)
    return _font_cache[key]

def measure_text(text, font):
    dummy = Image.new('RGBA', (1,1)); d = ImageDraw.Draw(dummy)
    bbox = d.textbbox((0,0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

# ---- Toast PNG ----
def render_toast_png(label, topic):
    temp = Image.new('RGBA', (PANEL_W, PANEL_H), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp)
    td.rectangle([(BORDER_W, 0), (PANEL_W, PANEL_H)], fill=(18, 22, 30, PANEL_BG_A))
    td.rectangle([(0, 0), (BORDER_W, PANEL_H)], fill=YELLOW)
    cx_r = PANEL_W - TOAST_X_MARGIN - TOAST_X_SIZE
    cx_t = TOAST_X_MARGIN
    td.line([(cx_r, cx_t), (cx_r + TOAST_X_SIZE, cx_t + TOAST_X_SIZE)], fill=TOAST_X_DIM, width=2)
    td.line([(cx_r + TOAST_X_SIZE, cx_t), (cx_r, cx_t + TOAST_X_SIZE)], fill=TOAST_X_DIM, width=2)
    f1 = get_font(LINE1_SIZE, True)
    f2 = get_font(LINE2_SIZE, False)
    x = BORDER_W + PAD_X
    y1 = PAD_Y; y2 = y1 + LINE1_SIZE + LINE_GAP - 2
    td.text((x, y1), label, font=f1, fill=YELLOW)
    td.text((x, y2), topic, font=f2, fill=GREEN)
    mask = Image.new('L', (PANEL_W, PANEL_H), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([(0, 0), (PANEL_W, PANEL_H)], radius=TOAST_CORNER_R, fill=255)
    rgba = temp.split()
    new_alpha = Image.new('L', (PANEL_W, PANEL_H), 0)
    new_alpha.paste(rgba[3], (0, 0), mask)
    temp.putalpha(new_alpha)
    img = temp
    shadow = Image.new('RGBA', (PANEL_W, PANEL_H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([(0, 0), (PANEL_W, PANEL_H)], radius=TOAST_CORNER_R, fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))
    out = Image.new('RGBA', (PANEL_W + 16, PANEL_H + 16), (0, 0, 0, 0))
    out.paste(shadow, (8, 8), shadow)
    out.paste(img, (0, 0), img)
    return np.array(out)

# ---- Phrases / chunking ----
def chunk_words(words, max_words=7, max_pause=0.40):
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        next_pause = (words[i+1]['start'] - w['end']) if i+1 < len(words) else 99
        if len(cur) >= max_words or i == len(words)-1 or next_pause > max_pause:
            chunks.append(cur); cur = []
    return chunks

def build_phrases(cfg):
    drop = set(cfg.get('drop_words', []))
    patches = cfg.get('patches', {})
    phrases = []
    for entry in cfg['subtitles']:
        v_start = entry['v_start']; v_end = entry['v_end']
        if 'override_text' in entry:
            tokens = entry['override_text'].split()
            n = len(tokens); total = v_end - v_start
            words = [{'word': t, 'start': v_start + total*i/n, 'end': v_start + total*(i+1)/n}
                     for i, t in enumerate(tokens)]
            phrases.append({'words': words, 't0': v_start, 't1': v_end,
                            'full_text': entry['override_text'].strip()})
            continue
        words = json.loads(Path(entry['words_json']).read_text())
        if not words: continue
        for chunk in chunk_words(words):
            adj = []
            for w in chunk:
                w_clean = w['word'].strip().rstrip('.,;:!?').strip()
                if w_clean in drop: continue
                token = patches.get(w['word'].strip(), w['word']).strip()
                adj.append({'word': token, 'start': v_start + w['start'], 'end': v_start + w['end']})
            if not adj: continue
            t0 = adj[0]['start']
            t1 = min(v_end, adj[-1]['end'] + 0.10)
            phrases.append({'words': adj, 't0': t0, 't1': t1,
                            'full_text': ' '.join(a['word'] for a in adj).strip()})
    return phrases

# ---- Subtitle render ----
def compute_panel_size(cfg):
    body_h = SUB_PAD_BODY_TOP + SUB_FONT_SIZE + SUB_PAD_BODY_BOTTOM
    panel_h = SUB_HEADER_H + body_h
    return cfg.get('fixed_panel_w', 1320), panel_h

_sub_cache = {}
def render_subtitle(panel_w, panel_h, phrase_idx, phrase, n_visible, cursor_on):
    key = (phrase_idx, n_visible, cursor_on)
    if key in _sub_cache: return _sub_cache[key]
    temp = Image.new('RGBA', (panel_w, panel_h), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp)
    td.rectangle([(0, SUB_HEADER_H), (panel_w, panel_h)], fill=PANEL_BG)
    td.rectangle([(0, 0), (panel_w, SUB_HEADER_H)], fill=HEADER_BG)
    cy = SUB_HEADER_H // 2
    for i, color in enumerate((DOT_RED, DOT_YELLOW, DOT_GREEN)):
        cx = DOT_LEFT + i * DOT_GAP
        td.ellipse([(cx-DOT_R, cy-DOT_R), (cx+DOT_R, cy+DOT_R)], fill=color)
    mask = Image.new('L', (panel_w, panel_h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([(0, 0), (panel_w, panel_h)], radius=SUB_CORNER_R, fill=255)
    rgba = temp.split()
    new_alpha = Image.new('L', (panel_w, panel_h), 0)
    new_alpha.paste(rgba[3], (0, 0), mask)
    temp.putalpha(new_alpha)
    img = temp
    d = ImageDraw.Draw(img)
    visible_words = ' '.join(w['word'] for w in phrase['words'][:n_visible])
    body = PROMPT_PREFIX + visible_words
    if cursor_on: body += ' _'
    body_x = SUB_PAD_X
    body_y = SUB_HEADER_H + SUB_PAD_BODY_TOP
    font = get_font(SUB_FONT_SIZE, True)
    d.text((body_x+2, body_y+2), body, font=font, fill=(0, 0, 0, 180))
    d.text((body_x,   body_y),   body, font=font, fill=GREEN_BRIGHT)
    arr = np.array(img)
    _sub_cache[key] = arr
    return arr

# ---- Animation curve ----
def toast_x(t, t_start, hold_x, off_x):
    t_in_end = t_start + SLIDE_IN
    t_out_start = t_in_end + HOLD
    t_out_end = t_out_start + SLIDE_OUT
    if t < t_start or t >= t_out_end: return None
    if t < t_in_end:
        return off_x + (hold_x - off_x) * (t - t_start) / SLIDE_IN
    if t < t_out_start: return hold_x
    return hold_x + (off_x - hold_x) * (t - t_out_start) / SLIDE_OUT

# ---- Composite ----
def composite_rgba(bgr, rgba_np, x, y):
    fh, fw = bgr.shape[:2]
    th, tw = rgba_np.shape[:2]
    x = int(round(x)); y = int(round(y))
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(fw, x + tw), min(fh, y + th)
    if x2 <= x1 or y2 <= y1: return
    sx1, sy1 = x1 - x, y1 - y
    sx2, sy2 = sx1 + (x2 - x1), sy1 + (y2 - y1)
    region = bgr[y1:y2, x1:x2]
    src = rgba_np[sy1:sy2, sx1:sx2]
    src_bgr = src[..., [2, 1, 0]]
    alpha = src[..., 3:4].astype(np.float32) / 255.0
    bgr[y1:y2, x1:x2] = (region.astype(np.float32) * (1 - alpha) +
                         src_bgr.astype(np.float32) * alpha).astype(np.uint8)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('config', help='YAML config path')
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())

    in_path = Path(cfg['input'])
    out_path = Path(cfg['output'])
    top_margin = cfg.get('toast_top_margin', 60)
    bottom_margin = cfg.get('sub_bottom_margin', 70)

    print(f'[1/4] rendering {len(cfg["toasts"])} toast PNGs')
    toast_imgs = {}
    for ts in cfg['toasts']:
        toast_imgs[ts['slug']] = render_toast_png(ts['label'], ts['topic'])

    print(f'[2/4] building phrase list')
    phrases = build_phrases(cfg)
    panel_w, panel_h = compute_panel_size(cfg)
    print(f'  {len(phrases)} phrases, panel = {panel_w}x{panel_h}')

    cap = cv2.VideoCapture(str(in_path))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f'[3/4] cv2 composite (input {w}x{h}, {n} frames)')

    toast_meta = []
    for ts in cfg['toasts']:
        img = toast_imgs[ts['slug']]
        tw, th = img.shape[1], img.shape[0]
        toast_meta.append((ts['slug'], ts['t_start'], LEFT_MARGIN, -tw))

    tmp_v = out_path.with_name('_tmp_overlay.mp4')
    enc = subprocess.Popen([
        'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{w}x{h}', '-pix_fmt', 'bgr24', '-r', str(FPS), '-i', '-',
        '-c:v', 'libx264', '-crf', '18', '-preset', 'medium',
        '-r', str(FPS), '-g', str(FPS), '-keyint_min', str(FPS),
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', str(tmp_v)
    ], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    fi = 0; last_pct = -1
    while True:
        ret, frame = cap.read()
        if not ret: break
        t = fi / FPS
        for slug, t_start, hold_x, off_x in toast_meta:
            x = toast_x(t, t_start, hold_x, off_x)
            if x is None: continue
            composite_rgba(frame, toast_imgs[slug], x, top_margin)
        for pi, p in enumerate(phrases):
            if p['t0'] <= t < p['t1']:
                n_visible = sum(1 for w in p['words'] if w['start'] <= t)
                cursor_on = int(t * 2) % 2 == 0
                sub = render_subtitle(panel_w, panel_h, pi, p, n_visible, cursor_on)
                sub_x = (w - sub.shape[1]) // 2
                sub_y = h - sub.shape[0] - bottom_margin
                composite_rgba(frame, sub, sub_x, sub_y)
                break
        enc.stdin.write(frame.tobytes())
        fi += 1
        pct = int(fi * 100 / n)
        if pct != last_pct and pct % 10 == 0:
            print(f'  {pct}% ({fi}/{n})', flush=True)
            last_pct = pct
    cap.release(); enc.stdin.close(); enc.wait()

    print('[4/4] mux audio (-c copy)')
    cmd = ['ffmpeg', '-y', '-i', str(tmp_v), '-i', str(in_path),
           '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy',
           '-shortest', '-movflags', '+faststart', str(out_path)]
    subprocess.check_call(cmd, stderr=subprocess.DEVNULL)
    tmp_v.unlink(missing_ok=True)
    import os
    print(f'  done → {out_path} ({os.path.getsize(out_path)/1e6:.1f} MB)')

if __name__ == '__main__':
    main()
