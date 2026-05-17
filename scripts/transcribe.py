"""Transcribe one or more source videos with faster-whisper (medium.en).

Writes <out-dir>/<source-stem>.json per input with word-level timestamps.

Example:
    python3 scripts/transcribe.py \\
        --srcs sources/IMG_*.MOV \\
        --out-dir work/transcripts
"""
from __future__ import annotations
from faster_whisper import WhisperModel
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse, json, time

# Whisper mis-hears that show up in AI-builder contexts.
# Extend per event.
PATCH = {"cloud": "Claude", "Cloud": "Claude"}

def transcribe_one(args_tuple):
    src_path, out_dir, model_size = args_tuple
    src = Path(src_path)
    t0 = time.time()
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segs, info = model.transcribe(
        str(src), word_timestamps=True, vad_filter=True, language="en"
    )
    words = []
    text_parts = []
    for s in segs:
        text_parts.append(s.text.strip())
        for w in (s.words or []):
            ww = (w.word or "").strip()
            for k, v in PATCH.items():
                if k in ww:
                    ww = ww.replace(k, v)
            words.append({"start": float(w.start), "end": float(w.end), "word": ww})
    full = " ".join(text_parts)
    for k, v in PATCH.items():
        full = full.replace(k, v)
    out = {
        "source": str(src),
        "duration": float(info.duration),
        "language": info.language,
        "text": full.strip(),
        "words": words,
    }
    dst = Path(out_dir) / f"{src.stem}.json"
    dst.write_text(json.dumps(out, indent=1))
    return f"{src.stem}: {len(words)} words in {time.time()-t0:.1f}s"

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--srcs", nargs="+", required=True,
                    help="one or more source video paths (mov, mp4)")
    ap.add_argument("--out-dir", default="work/transcripts",
                    help="output dir for per-source JSON (default: work/transcripts)")
    ap.add_argument("--model", default="medium.en",
                    help="faster-whisper model size (default: medium.en)")
    ap.add_argument("--workers", type=int, default=3,
                    help="parallel workers (default: 3)")
    a = ap.parse_args()

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    work = [(s, str(out_dir), a.model) for s in a.srcs]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for line in ex.map(transcribe_one, work):
            print(line, flush=True)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
