#!/usr/bin/env python3
"""Puntua els posts descarregats, tria els millors candidats i en descarrega el mitjà.

Puntuació (adaptada d'instagram-research):
  interacció = likes + 3 × comentaris + 0,1 × visualitzacions
  velocitat  = interacció / (hores des de la publicació + 2) ** 0.8
Es prioritza la velocitat: un post que acumula interacció ràpid té més potencial viral.

Filtres: ni repetits ni el mateix autor en `min_days_between_same_author` dies,
màxim `max_age_days` d'antiguitat, màxim `max_views` visualitzacions i un autor per candidat.

Estratègia «abans que sigui viral»: només reels recents (poques hores/dies) que encara no han explotat.
Si es reposteja un reel que ja té milions de visualitzacions, Instagram el detecta com a duplicat i a qui
no ens segueix li ensenya l'original. Si arribem abans, el nostre competeix.

Als reels se'ls afegeix una pantalla negra final amb la pregunta de la descripció (scripts/end_card.py).
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path

import requests

import caption
import math
from end_card import add_end_card, question_from_caption
from viral_score import score as viral_score

UTC = dt.timezone.utc


def parse_time(value) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def num(post: dict, *keys) -> float:
    for k in keys:
        v = post.get(k)
        if isinstance(v, (int, float)) and v >= 0:
            return float(v)
    return 0.0


def engagement(post: dict) -> float:
    likes = num(post, "likesCount")
    comments = num(post, "commentsCount")
    views = num(post, "videoPlayCount", "videoViewCount")
    return likes + 3 * comments + 0.1 * views


def caption_for(post: dict, config: dict, style: str) -> str:
    return caption.build(post, style, config["account"])

def download(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  No s'ha pogut descarregar {url[:60]}…: {e}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--config", default="config/sources.json")
    ap.add_argument("--history", default="data/history.json")
    ap.add_argument("--output", required=True)
    ap.add_argument("--media-dir", required=True)
    args = ap.parse_args()

    config = json.loads(Path(args.config).read_text())
    history = json.loads(Path(args.history).read_text()).get("published", [])
    posts = json.loads(Path(args.input).read_text())
    now = dt.datetime.now(UTC)

    out_path = Path(args.output)
    existing = json.loads(out_path.read_text()).get("candidates", []) if out_path.exists() else []
    seen_codes = {h.get("shortCode") for h in history}
    for f in out_path.parent.glob("*.json"):  # no tornar a proposar candidats ja enviats (de qualsevol dia)
        seen_codes |= {c.get("shortCode") for c in json.loads(f.read_text()).get("candidates", [])}
    want = int(os.environ.get("CANDIDATES") or config.get("candidates_per_day", 4))
    reels_only = config.get("reels_only", False)
    recent_authors = {
        h.get("author", "").lower()
        for h in history
        if (t := parse_time(h.get("published_at")))
        and now - t < dt.timedelta(days=config.get("min_days_between_same_author", 14))
    }
    excluded = {a.lower() for a in config.get("excluded_authors", [])} | {config["account"].lower()}
    max_age = dt.timedelta(days=int(os.environ.get("MAX_AGE_DAYS") or config.get("max_age_days", 7)))
    min_age = dt.timedelta(hours=config.get("min_age_hours", 0))
    max_views = int(config.get("max_views", 0))
    keywords = [k.lower() for k in config.get("required_keywords", [])]
    strong = [k.lower() for k in config.get("strong_keywords", [])]
    excluded_words = [k.lower() for k in config.get("excluded_keywords", [])]
    blocked = [k.lower() for k in config.get("blocked_keywords", [])]  # IA, motos, anuncis de venda, publicitat

    def is_relevant(post: dict) -> bool:
        """Família Mustang (inclosos Shelby, GT350, GT500…), sense pickups ni el Shelby Cobra clàssic."""
        text = " ".join([post.get("caption") or "", " ".join(post.get("hashtags") or [])]).lower()
        if keywords and not any(k in text for k in keywords):
            return False
        if any(k in text + " " for k in blocked):
            return False
        if any(k in text for k in excluded_words) and not any(k in text for k in strong):
            return False
        return True

    scored, unique = [], {}
    for p in posts:
        code, author = p.get("shortCode"), (p.get("ownerUsername") or "").lower()
        t = parse_time(p.get("timestamp"))
        if not code or not author or not t or code in unique:
            continue
        unique[code] = p
        if code in seen_codes or author in recent_authors or author in excluded:
            continue
        if not (min_age <= now - t <= max_age) or not is_relevant(p):
            continue
        if reels_only and not p.get("videoUrl"):
            continue
        views = num(p, "videoPlayCount", "videoViewCount")
        if max_views and views > max_views:  # ja s'ha fet viral: Instagram ensenyaria l'original i no el nostre
            continue
        hours = max((now - t).total_seconds() / 3600, 0)
        p["_engagement"] = engagement(p)
        p["_velocity"] = p["_engagement"] / (hours + 2) ** 0.8
        # criteris de l'estudi de reels virals: clàssics, nit, so original… pugen; drift, no-Mustang… baixen
        vs, _ = viral_score({**p, "views": p.get("videoPlayCount") or p.get("videoViewCount") or 0,
                             "original_audio": (p.get("musicInfo") or {}).get("uses_original_audio")})
        bonus = vs - math.log10(max(p.get("videoPlayCount") or p.get("videoViewCount") or 1, 1))
        p["_velocity"] *= 10 ** bonus
        p["_age_hours"] = round(hours, 1)
        scored.append(p)

    scored.sort(key=lambda p: p["_velocity"], reverse=True)
    print(f"{len(unique)} posts únics, {len(scored)} passen els filtres")

    media_dir = Path(args.media_dir)
    previous = sum(len(json.loads(f.read_text()).get("candidates", []))
                   for f in out_path.parent.glob("*.json"))
    candidates, used_authors = [], {c["author"].lower() for c in existing}
    for p in scored:
        if len(candidates) >= want:
            break
        author = p["ownerUsername"].lower()
        if author in used_authors:
            continue
        is_video = bool(p.get("videoUrl"))
        src = p.get("videoUrl") if is_video else p.get("displayUrl")
        if not src:
            continue
        dest = media_dir / f"{p['shortCode']}.{'mp4' if is_video else 'jpg'}"
        if not download(src, dest):
            continue
        used_authors.add(author)
        style = caption.STYLES[(previous + len(candidates)) % len(caption.STYLES)]
        text = caption_for(p, config, style)
        card = None
        if is_video and config.get("end_card", True):  # pantalla negra final amb la pregunta de la descripció
            card = question_from_caption(text)
            if not add_end_card(dest, card):
                card = None
        candidates.append({
            "shortCode": p["shortCode"],
            "author": p["ownerUsername"],
            "original_url": p.get("url") or f"https://www.instagram.com/p/{p['shortCode']}/",
            "media_type": "REELS" if is_video else "IMAGE",
            "media_path": dest.as_posix(),
            "likes": int(num(p, "likesCount")),
            "comments": int(num(p, "commentsCount")),
            "views": int(num(p, "videoPlayCount", "videoViewCount")),
            "age_hours": p["_age_hours"],
            "velocity": round(p["_velocity"], 1),
            "original_caption": (p.get("caption") or "")[:500],
            "caption_style": style,
            "caption": text,
            "end_card": card,
            "status": "pending",
        })

    out = {"generated_at": now.isoformat(), "candidates": existing + candidates}  # s'afegeix, mai se sobreescriu
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    for c in candidates:
        print(f"  @{c['author']}: {c['likes']} likes, {c['views']} views, {c['age_hours']} h, velocitat {c['velocity']}")
    print(f"{len(candidates)} candidats desats a {args.output}")


if __name__ == "__main__":
    main()
