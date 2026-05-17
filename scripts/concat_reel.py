"""
Concat intro + 6 cuts + outro into final reel.

Per memory `feedback_ffmpeg_concat_av_drift`: enforce per-segment
apad,atrim=duration=<vid_dur> before concat so audio doesn't drift.
Per memory `feedback_light_vignette_pi5`: vignette=PI/5 post-concat.
Per memory `feedback_aac_intersample_tp_lift`: final TP target -3 dBTP.

Output: renders/ralphthon_hackathon_v1.mp4
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTRO = ROOT / "work/intro/intro.mp4"
OUTRO = ROOT / "work/outro/outro.mp4"
CUTS_DIR = ROOT / "work/cuts_v3_overlaid"
OUT = ROOT / "renders/ralphthon_hackathon_v3.mp4"

def probe_dur(p: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    segs = [INTRO] + sorted(CUTS_DIR.glob("c_*.mp4")) + [OUTRO]
    for s in segs:
        if not s.exists():
            print(f"MISSING: {s}", file=sys.stderr)
            sys.exit(1)
    durs = [probe_dur(s) for s in segs]
    print("segments:")
    for s, d in zip(segs, durs):
        print(f"  {d:7.3f}s  {s.name}")
    total = sum(durs)
    print(f"total raw: {total:.3f}s")

    # Build filter_complex with per-segment apad/atrim and concat at the end.
    # No xfade . keep it punchy with hard cuts (per user: "fast and upbeat").
    parts = []
    n = len(segs)
    inputs = []
    for i, s in enumerate(segs):
        inputs += ["-i", str(s)]
    # Re-time + normalize per segment
    for i, d in enumerate(durs):
        parts.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1,fps=30,setpts=PTS-STARTPTS[v{i}];"
        )
        parts.append(
            f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,"
            f"apad,atrim=duration={d:.6f},asetpts=PTS-STARTPTS[a{i}];"
        )
    # concat
    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(n))
    parts.append(f"{concat_inputs}concat=n={n}:v=1:a=1[vc][ac];")
    # post: vignette + final loudnorm
    parts.append("[vc]vignette=PI/5[vout];")
    parts.append("[ac]loudnorm=I=-16:TP=-3:LRA=11[aout]")
    fc = "".join(parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "[aout]",
        "-r", "30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", "-preset", "slow",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        str(OUT),
    ]
    print(">>", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR tail:\n" + "\n".join(r.stderr.splitlines()[-50:]), file=sys.stderr)
        sys.exit(r.returncode)
    # Final probe
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration,size",
         "-of", "default=noprint_wrappers=0", str(OUT)],
        capture_output=True, text=True,
    )
    print(p.stdout)
    print(f"WROTE {OUT}")

if __name__ == "__main__":
    main()
