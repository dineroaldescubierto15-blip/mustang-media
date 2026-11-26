#!/usr/bin/env python3
"""Separa cada reel en plans i en mesura el ritme, el primer segon i el so.

Per cada reel: descarrega el vídeo (temporalment), detecta els talls de pla amb ffmpeg,
calcula el volum, el moviment del primer segon i genera un full amb 8 fotogrames
(un per cada part del vídeo) per poder-lo revisar visualment. El vídeo no es guarda.
"""
import argparse
import json
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=240).stderr


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,codec_type",
                          "-of", "json", str(path)], capture_output=True, text=True).stdout
    d = json.loads(out or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in d.get("streams", []))
    return {"duration": float(d.get("format", {}).get("duration") or 0), "width": v.get("width"),
            "height": v.get("height"), "has_audio": has_audio}


def cuts(path: Path, threshold: float = 0.3) -> list[float]:
    err = run(["ffmpeg", "-hide_banner", "-i", str(path), "-filter:v",
               f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"])
    return [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", err)]


def motion_first_second(path: Path) -> float:
    """Mitjana del canvi entre fotogrames durant el primer segon (0 = imatge quieta)."""
    err = run(["ffmpeg", "-hide_banner", "-t", "1.2", "-i", str(path), "-filter:v",
               "select='gte(scene,0)',metadata=print", "-an", "-f", "null", "-"])
    vals = [float(v) for v in re.findall(r"lavfi.scene_score=([\d.]+)", err)]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def loudness(path: Path) -> dict:
    err = run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"])
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", err)
    peak = re.search(r"max_volume: (-?[\d.]+) dB", err)
    first = run(["ffmpeg", "-hide_banner", "-t", "2", "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"])
    first_mean = re.search(r"mean_volume: (-?[\d.]+) dB", first)
    return {"mean_db": float(mean.group(1)) if mean else None, "max_db": float(peak.group(1)) if peak else None,
            "first2s_db": float(first_mean.group(1)) if first_mean else None}


def contact_sheet(path: Path, duration: float, out: Path) -> None:
    times = [0.3] + [duration * f for f in (0.12, 0.25, 0.4, 0.55, 0.7, 0.85, 0.97)]
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, t in enumerate(times):
            f = Path(tmp) / f"{i}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                            "-vf", "scale=160:-2", str(f)], timeout=60)
            if f.exists():
                frames.append(str(f))
        if not frames:
            return
        inputs = sum((["-i", f] for f in frames), [])
        n = len(frames)
        layout = "|".join(f"{(i % 4) * 160}_{(i // 4) * 284}" for i in range(n))
        filt = "".join(f"[{i}:v]scale=160:284:force_original_aspect_ratio=decrease,pad=160:284[v{i}];" for i in range(n))
        filt += "".join(f"[v{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}:fill=black"
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", filt, "-q:v", "6", str(out)],
                       timeout=60)


def analyze(post: dict, sheets_dir: Path) -> dict:
    res = {"shortCode": post["shortCode"]}
    with tempfile.TemporaryDirectory() as tmp:
        video = Path(tmp) / "v.mp4"
        try:
            r = requests.get(post["videoUrl"], timeout=120)
            r.raise_for_status()
            video.write_bytes(r.content)
        except requests.RequestException as e:
            res["error"] = f"descàrrega: {e}"
            return res
        info = probe(video)
        dur = info["duration"] or post.get("duration") or 0
        c = [t for t in cuts(video) if t > 0.05]
        res.update(info)
        res["cut_times"] = c
        res["n_cuts"] = len(c)
        res["shots"] = len(c) + 1
        res["avg_shot_s"] = round(dur / (len(c) + 1), 2) if dur else None
        res["cuts_per_10s"] = round(len(c) / dur * 10, 2) if dur else None
        res["first_cut_s"] = c[0] if c else None
        res["motion_1s"] = motion_first_second(video)
        if info["has_audio"]:
            res.update(loudness(video))
        contact_sheet(video, dur, sheets_dir / f"{post['shortCode']}.jpg")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--posts", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--sheets", required=True)
    args = ap.parse_args()
    posts = json.loads(Path(args.posts).read_text())
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda p: analyze(p, Path(args.sheets)), posts))
    ok = sum(1 for r in results if "error" not in r)
    print(f"{ok}/{len(results)} reels analitzats")
    Path(args.output).write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
