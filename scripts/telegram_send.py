#!/usr/bin/env python3
"""Envia per Telegram els candidats del dia.

Per cada candidat: el vídeo o la foto amb les dades i els botons ✅ / ❌, i just a sota
l'esborrany de la descripció que es publicarà. Després actualitza el missatge fixat amb la cua.
"""
import argparse
import os
from pathlib import Path

from common import (CONFIG_FILE, ROOT, STATE_FILE, Telegram, chat_id, header, load_json, save_json,
                    update_pinned)

MAX_UPLOAD = 49 * 1024 * 1024  # límit de pujada dels bots de Telegram


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    args = ap.parse_args()

    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), chat_id()
    if not token or not chat:
        print("Falta TELEGRAM_BOT_TOKEN o el xat (cal enviar /start al bot); no s'envia res")
        return
    tg = Telegram(token)
    config, state = load_json(CONFIG_FILE, {}), load_json(STATE_FILE, {})

    path = Path(args.candidates)
    data = load_json(path, {"candidates": []})
    day = path.stem
    if not data["candidates"]:
        tg.call("sendMessage", chat_id=chat, text="🔍 Avui no s'ha trobat cap candidat de Mustang que passi els filtres.")
        return

    sent = 0
    for c in data["candidates"]:
        if c.get("message_id"):
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
                    msg = tg.call("sendVideo" if is_video else "sendPhoto",
                                  files={"video" if is_video else "photo": fh},
                                  chat_id=chat, caption=header(c), reply_markup=keyboard)
                c["message_kind"] = "media"
            else:
                msg = tg.call("sendMessage", chat_id=chat, text=header(c), reply_markup=keyboard,
                              disable_web_page_preview=True)
                c["message_kind"] = "text"
            c["message_id"] = msg["message_id"]
            draft = tg.call("sendMessage", chat_id=chat, reply_to_message_id=msg["message_id"],
                            text=f"📝 Esborrany de la descripció:\n\n{c['caption']}", disable_notification=True)
            c["caption_message_id"] = draft["message_id"]
            sent += 1
        except RuntimeError as e:
            print(f"Error enviant {c['shortCode']}: {e}")

    save_json(path, data)
    update_pinned(tg, state, config)
    save_json(STATE_FILE, state)
    print(f"Enviats {sent} candidats a Telegram")


if __name__ == "__main__":
    main()
