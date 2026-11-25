#!/usr/bin/env python3
"""Processa un clic o una ordre que Make ha rebut de Telegram i ha reenviat a GitHub (repository_dispatch)."""
import json
import os
from urllib.parse import unquote

from common import (CONFIG_FILE, STATE_FILE, Telegram, handle_update, load_json, save_json, sync_drafts,
                    update_pinned)


def as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def main() -> None:
    event = json.load(open(os.environ["GITHUB_EVENT_PATH"]))
    p = event.get("client_payload") or {}
    print("Rebut:", p.get("cb_data") or p.get("text") or p)
    if p.get("cb_data"):
        update = {"callback_query": {"id": p.get("cb_id"), "data": p["cb_data"],
                                     "message": {"message_id": as_int(p.get("cb_msg")),
                                                 "chat": {"id": as_int(p.get("cb_chat"))}}}}
    elif p.get("text"):
        update = {"message": {"text": unquote(p["text"]), "chat": {"id": as_int(p.get("chat")),
                                                         "type": p.get("chat_type") or "private"}}}
    else:
        print("Esdeveniment sense dades útils:", p)
        return

    tg = Telegram(os.environ["TELEGRAM_BOT_TOKEN"])
    config, state = load_json(CONFIG_FILE, {}), load_json(STATE_FILE, {})
    handle_update(tg, state, update)
    if state.get("chat_id"):
        sync_drafts(tg, state["chat_id"])
    update_pinned(tg, state, config)
    save_json(STATE_FILE, state)
    print("Processat:", p.get("cb_data") or p.get("text"))


if __name__ == "__main__":
    main()
