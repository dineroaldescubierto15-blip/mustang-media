#!/usr/bin/env python3
"""Recull reels virals del nínxol Mustang per estudiar-ne els patrons.

Busca a molts hashtags amb Apify, aplica el filtre de rellevància, treu duplicats i es queda
amb els N reels amb més visualitzacions. Desa també les dades del so (música o so original).
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests

from relevance import make_filter

ACTOR = "apify~instagram-hashtag-scraper"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/sources.json")
    ap.add_argument("--hashtags", required=True, help="llista separada per comes")
    ap.add_argument("--per-hashtag", type=int, default=50)
    ap.add_argument("--top", type=int, default=200)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    token = os.environ.get("APIFY_TOKEN") or sys.exit("Falta APIFY_TOKEN")
    config = json.loads(Path(args.config).read_text())
    relevant = make_filter(config)
    tags = [t.strip().lstrip("#") for t in args.hashtags.split(",") if t.strip()]

    url = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
    payload = {"hashtags": tags, "resultsType": "reels", "resultsLimit": args.per_hashtag}
    resp = requests.post(url, params={"token": token}, json=payload, timeout=900)
    resp.raise_for_status()
    items = resp.json()
    print(f"{len(items)} resultats de {len(tags)} hashtags")

    seen, posts = set(), []
    for p in items:
        code = p.get("shortCode")
        if not code or code in seen or not p.get("videoUrl") or not relevant(p):
            continue
        seen.add(code)
        views = p.get("videoPlayCount") or p.get("videoViewCount") or 0
        music = p.get("musicInfo") or {}
        posts.append({
            "shortCode": code,
            "author": p.get("ownerUsername"),
            "url": p.get("url") or f"https://www.instagram.com/reel/{code}/",
            "timestamp": p.get("timestamp"),
            "views": views,
            "likes": max(p.get("likesCount") or 0, 0),
            "comments": p.get("commentsCount") or 0,
            "duration": p.get("videoDuration"),
            "caption": (p.get("caption") or "")[:600],
            "hashtags": p.get("hashtags") or [],
            "original_audio": music.get("uses_original_audio"),
            "song": music.get("song_name"),
            "artist": music.get("artist_name"),
            "videoUrl": p["videoUrl"],
            "displayUrl": p.get("displayUrl"),
        })
    out = Path(args.output)
    if out.exists():  # s'acumula amb els d'altres recollides del mateix dia
        prev = json.loads(out.read_text())
        posts += [p for p in prev if p["shortCode"] not in seen]
    posts.sort(key=lambda x: x["views"], reverse=True)
    posts = posts[: args.top]
    print(f"{len(posts)} reels rellevants (de {len(seen)} únics)")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(posts, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
