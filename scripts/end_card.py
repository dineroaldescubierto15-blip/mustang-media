#!/usr/bin/env python3
"""Afegeix al final de cada reel una pantalla negra amb una pregunta (per provocar comentaris).

La pregunta surt de la mateixa descripció del candidat (primera línia, sense emojis), perquè
vídeo i descripció diguin el mateix. Es fa servir en crear els candidats i, a mà, per a la cua:

  python scripts/end_card.py --queue        # candidats aprovats que encara no en tenen
"""
import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
GOLD = (201, 165, 74)
WHITE = (255, 255, 255)
GREY = (170, 170, 170)
SECONDS = 3.0
ACCOUNT = "@mustangemotion"

EMOJI_RX = re.compile("[\U0001F000-\U0001FFFF☀-➿️‍⬀-⯿←-⇿]")


def question_from_caption(caption: str) -> str:
    """'Rate this GT500 from 1 to 10 👇🔥\\nBe honest…' → 'Rate this GT500 from 1 to 10'."""
    first = (caption or "").strip().split("\n")[0]
    # «Mustang 🐎 Stock or modded? 👇» → «Stock or modded?»: si un tros entre emojis és una pregunta, és aquest
    parts = [re.sub(r"\s+", " ", p).strip(" -–—") for p in EMOJI_RX.split(first)]
    asks = [p for p in parts if p.endswith("?")]
    text = asks[0] if asks else " ".join(p for p in parts if p)
    text = re.sub(r"\b(\d+) to (\d+)\b", "\\1\u00a0to\u00a0\\2", text)  # «1 to 10» sempre a la mateixa línia
    return text or "Would you drive it?"


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    """Talla en línies i després les equilibra (que no quedi una paraula sola a l'última línia)."""
    lines = _greedy(draw, text, font, max_w)
    lo, hi = int(max_w * 0.4), max_w
    while lo < hi:
        mid = (lo + hi) // 2
        if len(_greedy(draw, text, font, mid)) <= len(lines):
            hi = mid
        else:
            lo = mid + 1
    return _greedy(draw, text, font, hi)


def _greedy(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split(" "):
        test = f"{cur} {word}".strip()
        if draw.textlength(test, font=font) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def render_card(question: str, w: int, h: int, out: Path) -> None:
    img = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(img)
    max_w = int(w * 0.84)
    size = int(w * 0.12)
    while True:  # la pregunta, tan gran com hi càpiga en un màxim de 4 línies
        font = ImageFont.truetype(str(FONTS / "Anton-Regular.ttf"), size)
        lines = _wrap(d, question.upper(), font, max_w)
        if len(lines) <= 4 or size < w * 0.06:
            break
        size = int(size * 0.9)
    line_h = int(size * 1.18)
    small = ImageFont.truetype(str(FONTS / "Inter-Bold.otf"), int(w * 0.042))
    tiny = ImageFont.truetype(str(FONTS / "Inter-Bold.otf"), int(w * 0.034))

    gap = int(w * 0.05)
    block_h = line_h * len(lines) + gap + int(w * 0.006) + gap + int(w * 0.05) + 2 * gap + int(w * 0.04)
    y = (h - block_h) // 2 - int(h * 0.03)  # una mica amunt: a baix hi ha la interfície dels reels
    for line in lines:
        d.text(((w - d.textlength(line, font=font)) / 2, y), line, font=font, fill=WHITE)
        y += line_h
    y += int(w * 0.05)
    bar = int(w * 0.12)  # filet daurat
    d.rectangle([(w - bar) / 2, y, (w + bar) / 2, y + max(int(w * 0.006), 3)], fill=GOLD)
    y += int(w * 0.006) + int(w * 0.05)
    cta = "COMMENT BELOW ↓"
    d.text(((w - d.textlength(cta, font=small)) / 2, y), cta, font=small, fill=GOLD)
    y += int(w * 0.05) + 2 * gap
    d.text(((w - d.textlength(ACCOUNT, font=tiny)) / 2, y), ACCOUNT, font=tiny, fill=GREY)
    img.save(out)


def _probe(path: Path) -> tuple[int, int, float, bool]:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    streams = json.loads(out)["streams"]
    v = next(s for s in streams if s["codec_type"] == "video")
    num, den = (v.get("avg_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den) if float(den or 0) else 30.0
    if not 10 <= fps <= 61:
        fps = 30.0
    w, h = int(v["width"]), int(v["height"])
    rot = str((v.get("tags") or {}).get("rotate", "")) or next(
        (str(int(sd.get("rotation", 0))) for sd in v.get("side_data_list", []) if "rotation" in sd), "0")
    if rot.lstrip("-") in ("90", "270"):
        w, h = h, w
    return w - w % 2, h - h % 2, round(fps, 3), any(s["codec_type"] == "audio" for s in streams)


def add_end_card(video: Path, question: str, seconds: float = SECONDS) -> bool:
    """Reescriu `video` amb la pantalla final. Si alguna cosa falla, deixa l'original intacte."""
    try:
        w, h, fps, audio = _probe(video)
        with tempfile.TemporaryDirectory() as tmp:
            card, out = Path(tmp) / "card.png", Path(tmp) / "out.mp4"
            render_card(question, w, h, card)
            norm = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p"
            fc = f"[0:v]{norm}[v0];[1:v]{norm},fade=in:st=0:d=0.35[v1];"
            cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(video),
                   "-loop", "1", "-framerate", str(fps), "-t", str(seconds), "-i", str(card)]
            if audio:
                cmd += ["-f", "lavfi", "-t", str(seconds), "-i", "anullsrc=r=44100:cl=stereo"]
                fc += ("[0:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a0];"
                       "[2:a]aformat=sample_fmts=fltp:channel_layouts=stereo[a1];"
                       "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
                maps = ["-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "128k"]
            else:
                fc += "[v0][v1]concat=n=2:v=1:a=0[v]"
                maps = ["-map", "[v]"]
            cmd += ["-filter_complex", fc, *maps, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            shutil.move(str(out), str(video))
        return True
    except (subprocess.CalledProcessError, StopIteration, KeyError, ValueError, OSError) as e:
        detail = getattr(e, "stderr", "") or e
        print(f"  ⚠️ No s'ha pogut afegir la pantalla final a {video.name}: {str(detail)[-300:]}")
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", action="store_true", help="aplica-la als candidats aprovats de la cua")
    ap.add_argument("--video")
    ap.add_argument("--question")
    args = ap.parse_args()
    if args.video:
        add_end_card(Path(args.video), args.question or "Would you drive it?")
        return
    if args.queue:
        for f in sorted((ROOT / "data" / "candidates").glob("*.json")):
            data = json.loads(f.read_text())
            changed = False
            for c in data["candidates"]:
                if c.get("status") != "approved" or c.get("end_card") or c.get("media_type") != "REELS":
                    continue
                q = question_from_caption(c["caption"])
                if add_end_card(ROOT / c["media_path"], q):
                    c["end_card"] = q
                    changed = True
                    print(f"  @{c['author']}: «{q}»")
            if changed:
                f.write_text(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
