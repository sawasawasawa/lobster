"""
v2 cut: PLAIN clip (no name strap drawtext, no silenceremove which desyncs).
Output goes to work/cuts_plain/c_NN.mp4 . overlay_terminal will add captions later.

Fix vs v1: silenceremove was removing audio without shortening video → drift.
For Mayank in v1, 1.32s pause shrunk in audio but not video, causing the desync
the user reported. Drop silenceremove entirely.
"""
from __future__ import annotations
import argparse, subprocess, shlex, sys
from pathlib import Path

def cut(src: Path, t_in: float, t_out: float, idx: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"c_{idx}.mp4"
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "eq=contrast=1.06:saturation=1.08:gamma=0.98"
    )
    af = "loudnorm=I=-16:TP=-3:LRA=11"
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{t_in:.3f}", "-to", f"{t_out:.3f}", "-i", str(src),
        "-filter_complex",
        f"[0:v]{vf}[v];[0:a]{af}[a]",
        "-map", "[v]", "-map", "[a]",
        "-r", "30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        str(dst),
    ]
    print(">>", " ".join(shlex.quote(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR tail:\n" + "\n".join(r.stderr.splitlines()[-20:]), file=sys.stderr)
        sys.exit(r.returncode)
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height:format=duration",
         "-of", "default=noprint_wrappers=0", str(dst)],
        capture_output=True, text=True,
    )
    print(p.stdout)
    return dst

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--in", dest="t_in", type=float, required=True)
    ap.add_argument("--out", dest="t_out", type=float, required=True)
    ap.add_argument("--idx", required=True)
    ap.add_argument("--out-dir", default="work/cuts_plain")
    a = ap.parse_args()
    cut(Path(a.src), a.t_in, a.t_out, a.idx, Path(a.out_dir))

if __name__ == "__main__":
    main()
