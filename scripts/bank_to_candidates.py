#!/usr/bin/env python3
"""Passa els N millors reels del banc als candidats del dia (amb descripció generada).

Escriu USE_BANK=true a $GITHUB_ENV si el banc ha cobert els candidats del dia (així no es gasta Apify).
"""
import argparse
import datetime as dt
import json
import os

import caption
from end_card import add_end_card, question_from_caption
from common import CANDIDATES_DIR, CONFIG_FILE, ROOT, load_json, now_utc, save_json

BANK = ROOT / "data" / "bank.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", required=True)
    ap.add_argument("--count", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="fes servir el banc encara que estigui desactivat")
    args = ap.parse_args()
    config = load_json(CONFIG_FILE, {})
    if not config.get("use_bank", False) and not args.force:
        # El banc són reels que ja tenen milions de visualitzacions: Instagram els tracta com a duplicats.
        print("Banc desactivat (use_bank: false): es fa servir la cerca de reels recents")
        return
    want = args.count or int(config.get("candidates_per_day", 8))
    bank = load_json(BANK, {"reels": []})
    avail = [r for r in bank["reels"] if r.get("status") == "banked"]
    if len(avail) < want:
        print(f"Al banc només hi ha {len(avail)} reels: es farà servir la cerca d'Apify")
        return

    out = CANDIDATES_DIR / f"{args.day}.json"
    data = load_json(out, {"generated_at": now_utc().isoformat(), "candidates": []})
    previous = sum(len(load_json(f, {"candidates": []})["candidates"]) for f in CANDIDATES_DIR.glob("*.json"))
    for i, r in enumerate(avail[:want]):
        style = caption.STYLES[(previous + i) % len(caption.STYLES)]
        post = {"shortCode": r["shortCode"], "ownerUsername": r["author"], "caption": r["caption_original"],
                "hashtags": r.get("hashtags", []), "media_type": "REELS"}
        age_h = 0.0
        if r.get("timestamp"):
            age_h = (now_utc() - dt.datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))).total_seconds() / 3600
        text = caption.build(post, style, config["account"])
        card = question_from_caption(text)
        if not add_end_card(ROOT / r["media_path"], card):
            card = None
        data["candidates"].append({
            "shortCode": r["shortCode"], "author": r["author"], "original_url": r["original_url"],
            "media_type": "REELS", "media_path": r["media_path"], "likes": r["likes"], "comments": r["comments"],
            "views": r["views"], "age_hours": round(age_h, 1), "velocity": r["score"],
            "original_caption": r["caption_original"], "caption_style": style,
            "caption": text, "status": "pending", "end_card": card,
            "source": "banc", "score_reasons": r.get("why", []),
        })
        r["status"] = "sent"
        r["sent_day"] = args.day
    save_json(out, data)
    save_json(BANK, bank)
    with open(os.environ.get("GITHUB_ENV", "/dev/null"), "a") as fh:
        fh.write("USE_BANK=true\n")
    print(f"{want} candidats del banc afegits a {out.name} (en queden {len(avail) - want})")


if __name__ == "__main__":
    main()
