#!/usr/bin/env python3
"""Crea el banc de reels a partir de l'estudi: puntua, tria els millors i en descarrega el vídeo."""
import argparse
import json
from pathlib import Path

import requests

from common import CANDIDATES_DIR, HISTORY_FILE, ROOT, load_json, save_json
from relevance import make_filter
from viral_score import score

BANK = ROOT / "data" / "bank.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", required=True, help="carpeta analysis/<data>")
    ap.add_argument("--size", type=int, default=40)
    ap.add_argument("--min-views", type=int, default=100_000)
    args = ap.parse_args()

    config = load_json(ROOT / "config" / "sources.json", {})
    relevant = make_filter(config)
    posts = json.loads((Path(args.study) / "posts.json").read_text())
    metrics = {m["shortCode"]: m for m in json.loads((Path(args.study) / "metrics.json").read_text())
               if "error" not in m}

    used = {h["shortCode"] for h in load_json(HISTORY_FILE, {"published": []})["published"]}
    for f in CANDIDATES_DIR.glob("*.json"):
        used |= {c["shortCode"] for c in load_json(f, {"candidates": []})["candidates"]}
    bank = load_json(BANK, {"reels": []})
    used |= {r["shortCode"] for r in bank["reels"]}

    scored = []
    for p in posts:
        if p["shortCode"] in used or (p.get("views") or 0) < args.min_views or not relevant(p):
            continue
        s, why = score(p, metrics.get(p["shortCode"]))
        scored.append((s, why, p))
    scored.sort(key=lambda x: -x[0])

    authors = {r["author"].lower() for r in bank["reels"]}
    added = 0
    for s, why, p in scored:
        if added >= args.size:
            break
        if (p.get("author") or "").lower() in authors:
            continue
        dest = ROOT / "media" / "bank" / f"{p['shortCode']}.mp4"
        try:
            r = requests.get(p["videoUrl"], timeout=120)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  No s'ha pogut descarregar @{p['author']}: {e}")
            continue
        if len(r.content) > 95 * 1024 * 1024:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        authors.add(p["author"].lower())
        bank["reels"].append({
            "shortCode": p["shortCode"], "author": p["author"], "original_url": p["url"],
            "views": p["views"], "likes": p["likes"], "comments": p["comments"],
            "timestamp": p.get("timestamp"), "caption_original": p.get("caption", "")[:500],
            "hashtags": p.get("hashtags", []), "score": s, "why": why,
            "media_path": dest.relative_to(ROOT).as_posix(), "status": "banked",
        })
        added += 1
        print(f"  {s:.2f} @{p['author']} {p['views']:,} views · {', '.join(why)}")
    bank["reels"].sort(key=lambda r: -r["score"])
    save_json(BANK, bank)
    print(f"{added} reels afegits al banc ({len(bank['reels'])} en total)")


if __name__ == "__main__":
    main()
