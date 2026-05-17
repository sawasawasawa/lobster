"""
Run overlay_terminal.py on a single plain cut.

Generates a per-cut YAML config with:
- one toast (top-left): label="> NAME", topic="project"
- one subtitle (bottom): words_json from sliced source transcript, v_start=0, v_end=cut_dur

Output: work/cuts_overlaid/c_NN.mp4
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import yaml

OVERLAY_SCRIPT = Path(__file__).resolve().parent / "overlay_terminal.py"
ROOT = Path(__file__).resolve().parent.parent

def slice_words(src_transcript: Path, t_in: float, t_out: float, out_json: Path):
    """Pick words from the source transcript whose [start,end] is within [t_in,t_out],
    shifted to t=0 = cut start."""
    src = json.loads(src_transcript.read_text())
    out_words = []
    for w in src["words"]:
        if w["end"] <= t_in: continue
        if w["start"] >= t_out: break
        out_words.append({
            "start": max(0.0, w["start"] - t_in),
            "end": min(t_out - t_in, w["end"] - t_in),
            "word": w["word"],
        })
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out_words, indent=1))
    print(f"  sliced {len(out_words)} words → {out_json.name}")
    return out_words

def probe_dur(p: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", required=True, help="path to plain cut mp4")
    ap.add_argument("--src-transcript", required=True, help="path to original source whisper JSON")
    ap.add_argument("--t-in", type=float, required=True, help="cut start in source time")
    ap.add_argument("--t-out", type=float, required=True, help="cut end in source time")
    ap.add_argument("--name", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--idx", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cut_path = Path(args.cut)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Slice word_timestamps for this cut
    words_json = ROOT / "work/words" / f"c_{args.idx}.json"
    slice_words(Path(args.src_transcript), args.t_in, args.t_out, words_json)

    # 2. Probe cut duration
    cut_dur = probe_dur(cut_path)

    # 3. Write per-cut YAML config
    cfg = {
        "input": str(cut_path),
        "output": str(out_path),
        # Vertical 1080 . full-width subtitle panel with side margins
        "fixed_panel_w": 1020,
        # Position toast at top, subs near bottom (away from face for vertical)
        "toast_top_margin": 110,
        "sub_bottom_margin": 220,
        "drop_words": ["like", "Like", "um", "Um", "uh", "Uh"],
        "patches": {"cloud": "Claude", "Cloud": "Claude"},
        "toasts": [{
            "slug": args.idx,
            "label": f"> {args.name.upper()}",
            "topic": args.topic,
            "t_start": 0.20,
        }],
        "subtitles": [{
            "words_json": str(words_json),
            "v_start": 0.0,
            "v_end": cut_dur,
        }],
    }
    cfg_path = ROOT / "work/overlay_configs" / f"c_{args.idx}.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    print(f"  wrote config → {cfg_path.name}")

    # 4. Run overlay_terminal.py
    print(f"  running overlay on {cut_path.name}…")
    r = subprocess.run(
        ["python3", str(OVERLAY_SCRIPT), str(cfg_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print("STDOUT:\n" + r.stdout, file=sys.stderr)
        print("STDERR:\n" + r.stderr, file=sys.stderr)
        sys.exit(r.returncode)
    print(r.stdout)

if __name__ == "__main__":
    main()
