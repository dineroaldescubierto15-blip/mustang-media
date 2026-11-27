#!/usr/bin/env python3
"""Versió TikTok dels reels aprovats i publicació a TikTok a través de Zernio (pla gratuït, API oficial auditada).

Cada reel aprovat per Telegram es publica a Instagram i, si `tiktok.enabled` és cert a config/sources.json,
també a TikTok, amb canvis perquè no sigui una còpia exacta:
  · un ganxo escrit als 3 primers segons (patrons de l'estudi de reels virals),
  · el crèdit de l'autor escrit al vídeo durant tot el clip,
  · la pantalla final amb la pregunta (scripts/end_card.py),
  · una descripció pròpia per a TikTok (paraules clau per a la cerca + 4-5 hashtags).

Secrets: ZERNIO_API_KEY (GitHub). Config: tiktok.account_id (l'ID del compte de TikTok dins de Zernio).
Ús manual:
  python scripts/tiktok.py accounts                     # llista els comptes connectats a Zernio
  python scripts/tiktok.py preview --video X --author Y # genera la versió TikTok d'un vídeo
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://zernio.com/api/v1"
WHITE, BLACK = (255, 255, 255), (0, 0, 0)


def ensure_deps() -> None:
    """Als workflows de publicació no hi ha ffmpeg ni Pillow: s'instal·len només quan cal."""
    if not shutil.which("ffmpeg"):
        subprocess.run("sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg", shell=True, check=True)
    try:
        import PIL  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pillow"], check=True)


# ---------------------------------------------------------------- textos

def _text(c: dict) -> str:
    return (c.get("original_caption") or "").lower()


def hook(c: dict) -> str:
    """Ganxo curt per als primers segons, triat pel tema del vídeo (estudi de reels virals)."""
    import caption
    car, _ = caption.detect({"caption": c.get("original_caption"), "hashtags": []})
    t = _text(c)
    seed = int(hashlib.md5(c.get("shortCode", "").encode()).hexdigest(), 16)
    if re.search(r"19[6-7]\d|\b6[4-9]\b|fastback|eleanor|classic|vintage|restor|barn find", t):
        options = ["They don't make them like this anymore", "Name a better classic", f"Pure {car} history"]
    elif re.search(r"night|lights|glow|dark", t):
        options = [f"{car} hits different at night", "Night drives only", "Built for the night"]
    elif re.search(r"exhaust|sound|loud|cold start|rev|supercharg|whine|straight pipe", t):
        options = ["Turn your sound ON", "This sounds CRAZY", "Listen to this"]
    elif re.search(r"pov|drive|driving|manual|shift", t):
        options = [f"POV: you finally got the {car}", "This is why we drive manual", "Sunday drive"]
    else:
        options = [f"Your daily dose of {car}", f"This {car} is different", "Built different"]
    return options[seed % len(options)]


def tiktok_caption(c: dict) -> str:
    import caption
    from end_card import question_from_caption
    car, specific = caption.detect({"caption": c.get("original_caption"), "hashtags": []})
    q = (c.get("end_card") or question_from_caption(c.get("caption", ""))).replace(" ", " ")
    tags = list(dict.fromkeys(["fordmustang", "mustang"] + specific[:1] + ["carsoftiktok", "musclecar"]))[:5]
    credit = c["author"]
    return (f"{q} 👇\n\nFord {car if car != 'Mustang' else 'Mustang'} 🐎\n"
            f"🎥 @{credit} on Instagram\n\n" + " ".join("#" + t for t in tags))


# ---------------------------------------------------------------- vídeo

def _overlay(text: str, w: int, h: int, out: Path, size_ratio: float, y_ratio: float, color=WHITE) -> None:
    from PIL import Image, ImageDraw, ImageFont
    from end_card import FONTS, _wrap
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size = int(w * size_ratio)
    font = ImageFont.truetype(str(FONTS / "Inter-Bold.otf"), size)
    lines = _wrap(d, text, font, int(w * 0.86))
    y = int(h * y_ratio)
    stroke = max(2, size // 9)
    for line in lines:
        x = (w - d.textlength(line, font=font)) / 2
        d.text((x, y), line, font=font, fill=color, stroke_width=stroke, stroke_fill=BLACK)
        y += int(size * 1.25)
    img.save(out)


def make_version(src: Path, dst: Path, hook_text: str, author: str, question: str, trim_end: float = 0) -> bool:
    """Crea la versió TikTok: ganxo (0-3,5 s) + crèdit + pantalla final.

    `trim_end`: segons a treure del final (la pantalla final que ja porta la versió d'Instagram)."""
    from end_card import _probe, add_end_card
    try:
        w, h, fps, _ = _probe(src)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    str(src)], capture_output=True, text=True, check=True).stdout)
        with tempfile.TemporaryDirectory() as tmp:
            hk, cr, out = Path(tmp) / "hook.png", Path(tmp) / "credit.png", Path(tmp) / "out.mp4"
            _overlay(hook_text, w, h, hk, 0.072, 0.17)
            _overlay(f"video: @{author}", w, h, cr, 0.032, 0.115, color=(235, 235, 235))
            fc = (f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1[b];"
                  "[1:v]format=rgba,fade=out:st=3.2:d=0.4:alpha=1[hk];"
                  "[b][hk]overlay=0:0:enable='lte(t,3.6)'[v1];[v1][2:v]overlay=0:0,format=yuv420p[v]")
            cmd = ["ffmpeg", "-y", "-v", "error", "-t", f"{max(dur - trim_end, 1):.3f}", "-i", str(src),
                   "-loop", "1", "-t", "4", "-i", str(hk),
                   "-loop", "1", "-i", str(cr), "-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
                   "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "128k",
                   "-movflags", "+faststart", str(out)]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            if not add_end_card(out, question):
                return False
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(out), str(dst))
        return True
    except (subprocess.CalledProcessError, OSError, ValueError, KeyError, StopIteration) as e:
        print(f"  ⚠️ No s'ha pogut fer la versió TikTok: {str(getattr(e, 'stderr', '') or e)[-300:]}")
        return False


# ---------------------------------------------------------------- Zernio

def _api(method: str, path: str, **kw):
    import requests
    key = os.environ.get("ZERNIO_API_KEY")
    if not key:
        raise RuntimeError("Falta el secret ZERNIO_API_KEY")
    r = requests.request(method, API + path, headers={"Authorization": f"Bearer {key}"}, timeout=120, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"Zernio {path}: {r.status_code} {r.text[:300]}")
    return r.json()


def upload(path: Path) -> str:
    import requests
    pre = _api("POST", "/media/presign", json={"filename": path.name, "contentType": "video/mp4",
                                               "size": path.stat().st_size})
    with path.open("rb") as fh:
        r = requests.put(pre["uploadUrl"], data=fh, headers={"Content-Type": "video/mp4"}, timeout=600)
    r.raise_for_status()
    return pre["publicUrl"]


def publish_candidate(c: dict, config: dict) -> str:
    """Fa la versió TikTok del candidat i la publica. Retorna l'ID del post de Zernio."""
    tk = config.get("tiktok", {})
    if not tk.get("account_id"):
        raise RuntimeError("Falta tiktok.account_id a config/sources.json")
    ensure_deps()
    from end_card import question_from_caption
    question = c.get("end_card") or question_from_caption(c.get("caption", ""))
    src = ROOT / c["media_path"]
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / f"{c['shortCode']}_tiktok.mp4"
        # el vídeo d'Instagram ja porta la pantalla final: es treu abans de fer la versió TikTok
        from end_card import SECONDS
        trim = SECONDS if c.get("end_card") else 0
        if not make_version(src, dst, hook(c), c["author"], question, trim_end=trim):
            raise RuntimeError("no s'ha pogut generar el vídeo")
        url = upload(dst)
    body = {
        "content": tiktok_caption(c),
        "mediaItems": [{"type": "video", "url": url}],
        "platforms": [{"platform": "tiktok", "accountId": tk["account_id"]}],
        "tiktokSettings": {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True, "allow_duet": False,
                           "allow_stitch": False, "content_preview_confirmed": True, "express_consent_given": True},
        "publishNow": True,
    }
    res = _api("POST", "/posts", json=body)
    return (res.get("post") or {}).get("_id", "")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("accounts")
    pv = sub.add_parser("preview")
    pv.add_argument("--video", required=True)
    pv.add_argument("--author", required=True)
    pv.add_argument("--caption", default="")
    pv.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "accounts":
        for a in _api("GET", "/accounts").get("accounts", []):
            print(a.get("platform"), a.get("_id"), a.get("username") or a.get("displayName") or "")
    elif args.cmd == "preview":
        from end_card import question_from_caption
        import caption
        c = {"shortCode": Path(args.video).stem, "author": args.author, "original_caption": args.caption}
        car, _ = caption.detect({"caption": args.caption, "hashtags": []})
        c["caption"] = caption.build({"shortCode": c["shortCode"], "ownerUsername": args.author, "caption": args.caption,
                                      "media_type": "REELS"}, "A", "mustangemotion")
        q = question_from_caption(c["caption"])
        c["end_card"] = q
        ok = make_version(Path(args.video), Path(args.out), hook(c), args.author, q)
        print(json.dumps({"ok": ok, "hook": hook(c), "question": q, "caption": tiktok_caption(c)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
