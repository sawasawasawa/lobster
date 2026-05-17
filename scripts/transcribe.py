"""Transcribe all 6 sources in parallel using faster-whisper medium.en"""
from faster_whisper import WhisperModel
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import json, sys, time

ROOT = Path(__file__).resolve().parent.parent
SRCS = [
    ROOT / "master_clips/IMG_1079.mov",
    ROOT / "master_clips/IMG_1080.mov",
    ROOT / "master_clips/IMG_1081.mov",
    ROOT / "master_clips/IMG_1082.MOV",
    ROOT / "master_clips/IMG_1083.MOV",
    ROOT / "master_clips/IMG_1084.MOV",
]
OUT = ROOT / "work/transcripts"
OUT.mkdir(parents=True, exist_ok=True)

# Patches: common whisper miss-hears
PATCH = {"cloud": "Claude", "Cloud": "Claude"}

def transcribe_one(src_path):
    src = Path(src_path)
    t0 = time.time()
    model = WhisperModel("medium.en", device="cpu", compute_type="int8")
    segs, info = model.transcribe(str(src), word_timestamps=True, vad_filter=True, language="en")
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
    dst = OUT / f"{src.stem}.json"
    dst.write_text(json.dumps(out, indent=1))
    return f"{src.stem}: {len(words)} words in {time.time()-t0:.1f}s"

if __name__ == "__main__":
    # 6 sources, do up to 3 in parallel (CPU-bound int8 ~stable)
    with ProcessPoolExecutor(max_workers=3) as ex:
        for line in ex.map(transcribe_one, SRCS):
            print(line, flush=True)
    print("DONE", flush=True)
