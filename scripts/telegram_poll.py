#!/usr/bin/env python3
"""Manteniment periòdic del bot (cada hora aproximadament, des de GitHub).

- Si Telegram NO té webhook (mode antic), llegeix els clics pendents amb getUpdates.
  Amb el webhook de Make actiu, els clics arriben a l'instant per telegram_event.py.
- Caduca els candidats pendents de fa més de 3 dies.
- Actualitza els esborranys de descripció i la llista fixada.
"""
import os

from common import (CONFIG_FILE, STATE_FILE, Telegram, expire_old, handle_update, load_json, save_json,
                    sync_drafts, sync_marks, update_pinned, webhook_active)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Encara no hi ha TELEGRAM_BOT_TOKEN; no hi ha res a fer")
        return
    tg = Telegram(token)
    config, state = load_json(CONFIG_FILE, {}), load_json(STATE_FILE, {})

    if webhook_active(tg):
        print("Webhook de Make actiu: els clics arriben a l'instant, no cal llegir-los")
    else:
        updates = tg.call("getUpdates", offset=state.get("offset", 0), timeout=0,
                          allowed_updates=["message", "callback_query"])
        for u in updates:
            state["offset"] = u["update_id"] + 1
            handle_update(tg, state, u)
        print(f"{len(updates)} actualitzacions processades")

    chat = state.get("chat_id")
    print(f"{expire_old(tg, chat)} candidats caducats")
    if chat:
        sync_marks(tg, chat)
        sync_drafts(tg, chat)
    update_pinned(tg, state, config)
    save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
