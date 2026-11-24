#!/usr/bin/env python3
"""Llegeix les respostes de Telegram i actualitza l'estat dels candidats.

- ✅ / ❌: desa la decisió, treu els botons i deixa escrit l'estat al missatge.
- /start: registra el xat del propietari.
- /cua: torna a enviar (i fixar) la llista de pendents i aprovats.
"""
import os

from common import (CANDIDATES_DIR, CONFIG_FILE, STATE_FILE, Telegram, load_json, mark_message, now_utc,
                    save_json, update_pinned)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Encara no hi ha TELEGRAM_BOT_TOKEN; no hi ha res a fer")
        return
    tg = Telegram(token)
    config, state = load_json(CONFIG_FILE, {}), load_json(STATE_FILE, {})

    updates = tg.call("getUpdates", offset=state.get("offset", 0), timeout=0,
                      allowed_updates=["message", "callback_query"])
    for u in updates:
        state["offset"] = u["update_id"] + 1

        msg = u.get("message")
        if msg and msg.get("chat", {}).get("type") == "private":
            text = (msg.get("text") or "").strip().lower()
            if text.startswith("/start") and not state.get("chat_id"):
                state["chat_id"] = msg["chat"]["id"]
                tg.call("sendMessage", chat_id=state["chat_id"],
                        text="👋 Bot de @mustangemotion configurat. T'enviaré cada dia els candidats per aprovar.")
            elif text.startswith("/cua") and msg["chat"]["id"] == state.get("chat_id"):
                state.pop("pinned_message_id", None)
                state.pop("pinned_text", None)
            continue

        cq = u.get("callback_query")
        if not cq or cq.get("message", {}).get("chat", {}).get("id") != state.get("chat_id"):
            continue  # només acceptem respostes del xat del propietari
        action, day, code = (cq.get("data") or "x|x|x").split("|", 2)
        path = CANDIDATES_DIR / f"{day}.json"
        data = load_json(path, {"candidates": []})
        cand = next((c for c in data["candidates"] if c["shortCode"] == code), None)
        if cand and cand.get("status", "pending") == "pending" and action in ("a", "r"):
            cand["status"] = "approved" if action == "a" else "rejected"
            cand["decided_at"] = now_utc().isoformat()
            save_json(path, data)
        if cand:
            mark_message(tg, state["chat_id"], cand)
        try:
            tg.call("answerCallbackQuery", callback_query_id=cq["id"],
                    text="Desat ✅" if cand else "Aquest candidat ja no existeix.")
        except RuntimeError:
            pass  # la consulta pot haver caducat; l'estat ja està desat

    update_pinned(tg, state, config)
    save_json(STATE_FILE, state)
    print(f"{len(updates)} actualitzacions processades")


if __name__ == "__main__":
    main()
