"""Concat intro + N overlaid cuts + outro into a final vertical reel.

Single filter_complex pass:
  . per-segment apad,atrim=duration=<video_dur> to prevent AAC concat drift
  . vignette=PI/5 post-concat
  . final loudnorm pass to I=-16 LUFS / TP=-3 dBFS

Example:
    python3 scripts/concat_reel.py \\
        --intro work/intro/intro.mp4 \\
        --outro work/outro/outro.mp4 \\
        --cuts-dir work/cuts_overlaid \\
        --out renders/reel.mp4
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

def probe_dur(p: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--intro", required=True, help="intro mp4 (5s vertical)")
    ap.add_argument("--outro", required=True, help="outro mp4 (5s vertical)")
    ap.add_argument("--cuts-dir", required=True,
                    help="directory containing c_*.mp4 overlaid cuts (sorted lexically)")
    ap.add_argument("--out", required=True, help="output mp4 path")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()

    intro = Path(a.intro); outro = Path(a.outro)
    cuts_dir = Path(a.cuts_dir); out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    segs = [intro] + sorted(cuts_dir.glob("c_*.mp4")) + [outro]
    for s in segs:
        if not s.exists():
            print(f"MISSING: {s}", file=sys.stderr); sys.exit(1)

    durs = [probe_dur(s) for s in segs]
    print("segments:")
    for s, d in zip(segs, durs):
        print(f"  {d:7.3f}s  {s.name}")
    total = sum(durs)
    print(f"total raw: {total:.3f}s")

    parts = []
    n = len(segs)
    inputs = []
    for i, s in enumerate(segs):
        inputs += ["-i", str(s)]
    for i, d in enumerate(durs):
        parts.append(
            f"[{i}:v]scale={a.width}:{a.height}:force_original_aspect_ratio=increase,"
            f"crop={a.width}:{a.height},setsar=1,fps={a.fps},setpts=PTS-STARTPTS[v{i}];"
        )
        parts.append(
            f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,"
            f"apad,atrim=duration={d:.6f},asetpts=PTS-STARTPTS[a{i}];"
        )
    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(n))
    parts.append(f"{concat_inputs}concat=n={n}:v=1:a=1[vc][ac];")
    parts.append("[vc]vignette=PI/5[vout];")
    parts.append("[ac]loudnorm=I=-16:TP=-3:LRA=11[aout]")
    fc = "".join(parts)

    cmd = [
        "ffmpeg", "-y", *inputs, "-filter_complex", fc,
        "-map", "[vout]", "-map", "[aout]", "-r", str(a.fps),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart", str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR tail:\n" + "\n".join(r.stderr.splitlines()[-50:]), file=sys.stderr)
        sys.exit(r.returncode)

    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration,size",
         "-of", "default=noprint_wrappers=0", str(out)],
        capture_output=True, text=True,
    )
    print(p.stdout)
    print(f"WROTE {out}")

if __name__ == "__main__":
    main()
