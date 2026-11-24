#!/usr/bin/env python3
"""Descarrega posts/reels recents de hashtags amb l'actor d'Apify instagram-hashtag-scraper.

Llegeix APIFY_TOKEN de l'entorn (a GitHub Actions ve del secret del repositori).
Fa rotació de hashtags: cada dia en consulta `hashtags_per_day` de la llista de config/sources.json.
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests

ACTOR = "apify~instagram-hashtag-scraper"


def hashtags_for_today(config: dict, day: dt.date) -> list[str]:
    tags = config["hashtags"]
    per_day = min(config.get("hashtags_per_day", len(tags)), len(tags))
    start = (day.toordinal() * per_day) % len(tags)
    return [tags[(start + i) % len(tags)] for i in range(per_day)]


def run_actor(token: str, hashtags: list[str], results_type: str, limit: int) -> list[dict]:
    url = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
    payload = {"hashtags": hashtags, "resultsType": results_type, "resultsLimit": limit}
    resp = requests.post(url, params={"token": token}, json=payload, timeout=600)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/sources.json")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("Falta APIFY_TOKEN")

    config = json.loads(Path(args.config).read_text())
    tags = hashtags_for_today(config, dt.date.today())
    limit = config.get("results_per_hashtag", 20)
    print(f"Hashtags d'avui: {', '.join('#' + t for t in tags)} ({limit} resultats cadascun)")

    items: list[dict] = []
    for results_type in config.get("content_types", ["reels"]):
        batch = run_actor(token, tags, results_type, limit)
        print(f"  {results_type}: {len(batch)} resultats")
        items.extend(batch)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(items, indent=1, default=str))
    print(f"Desat a {args.output}")


if __name__ == "__main__":
    main()
