#!/usr/bin/env python3
"""Envia per Telegram els candidats del dia, amb el vídeo o la foto i els botons ✅ / ❌."""
import argparse
import os
from pathlib import Path

from common import ROOT, Telegram, chat_id, load_json, save_json

MAX_UPLOAD = 49 * 1024 * 1024  # límit de pujada dels bots de Telegram


def summary(c: dict, i: int, total: int) -> str:
    views = f" · 👁 {c['views']:,}" if c.get("views") else ""
    return (
        f"🐎 Candidat {i}/{total} · @{c['author']}\n"
        f"❤️ {c['likes']:,} · 💬 {c['comments']:,}{views} · fa {c['age_hours']:.0f} h\n"
        f"🔗 {c['original_url']}\n\n"
        f"Caption:\n{c['caption']}"
    )[:1024]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    args = ap.parse_args()

    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), chat_id()
    if not token or not chat:
        print("Falta TELEGRAM_BOT_TOKEN o el xat (cal enviar /start al bot); no s'envia res")
        return
    tg = Telegram(token)

    path = Path(args.candidates)
    data = load_json(path, {"candidates": []})
    day = path.stem
    pending = [c for c in data["candidates"] if not c.get("message_id")]
    total = len(data["candidates"])
    if not total:
        tg.call("sendMessage", chat_id=chat, text="🔍 Avui no s'ha trobat cap candidat de Mustang que passi els filtres.")
        return

    for i, c in enumerate(data["candidates"], 1):
        if c not in pending:
            continue
        keyboard = {"inline_keyboard": [[
            {"text": "✅ Aprovar", "callback_data": f"a|{day}|{c['shortCode']}"},
            {"text": "❌ Descartar", "callback_data": f"r|{day}|{c['shortCode']}"},
        ]]}
        media = ROOT / c["media_path"]
        is_video = c["media_type"] == "REELS"
        try:
            if media.exists() and media.stat().st_size <= MAX_UPLOAD:
                with media.open("rb") as fh:
                    field = "video" if is_video else "photo"
                    msg = tg.call("sendVideo" if is_video else "sendPhoto", files={field: fh},
                                  chat_id=chat, caption=summary(c, i, total), reply_markup=keyboard)
            else:
                msg = tg.call("sendMessage", chat_id=chat, text=summary(c, i, total), reply_markup=keyboard)
        except RuntimeError as e:
            print(f"Error enviant {c['shortCode']}: {e}")
            continue
        c["message_id"] = msg["message_id"]

    save_json(path, data)
    print(f"Enviats {len(pending)} candidats a Telegram")


if __name__ == "__main__":
    main()
