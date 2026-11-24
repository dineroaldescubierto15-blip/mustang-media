#!/usr/bin/env python3
"""Llegeix les respostes de Telegram (botons ✅ / ❌ i /start) i actualitza l'estat dels candidats."""
import os

from common import CANDIDATES_DIR, STATE_FILE, Telegram, load_json, now_utc, save_json


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Encara no hi ha TELEGRAM_BOT_TOKEN; no hi ha res a fer")
        return
    tg = Telegram(token)
    state = load_json(STATE_FILE, {})
    offset = state.get("offset", 0)

    updates = tg.call("getUpdates", offset=offset, timeout=0, allowed_updates=["message", "callback_query"])
    changed = False
    for u in updates:
        state["offset"] = u["update_id"] + 1
        changed = True

        msg = u.get("message")
        if msg and msg.get("chat", {}).get("type") == "private" and (msg.get("text") or "").startswith("/start"):
            if not state.get("chat_id"):
                state["chat_id"] = msg["chat"]["id"]
                tg.call("sendMessage", chat_id=state["chat_id"],
                        text="👋 Bot de @mustangemotion configurat. T'enviaré cada dia els candidats per aprovar.")
            continue

        cq = u.get("callback_query")
        if not cq:
            continue
        if cq.get("message", {}).get("chat", {}).get("id") != state.get("chat_id"):
            continue  # només acceptem respostes del xat del propietari
        action, day, code = (cq.get("data") or "x|x|x").split("|", 2)
        path = CANDIDATES_DIR / f"{day}.json"
        data = load_json(path, {"candidates": []})
        cand = next((c for c in data["candidates"] if c["shortCode"] == code), None)
        if not cand:
            tg.call("answerCallbackQuery", callback_query_id=cq["id"], text="Aquest candidat ja no existeix.")
            continue

        if cand.get("status") in ("pending", "approved", "rejected"):
            cand["status"] = "approved" if action == "a" else "rejected"
            cand["decided_at"] = now_utc().isoformat()
            save_json(path, data)
        label = {"approved": "✅ Aprovat · a la cua", "rejected": "❌ Descartat",
                 "published": "📣 Ja publicat"}.get(cand["status"], cand["status"])
        try:
            tg.call("answerCallbackQuery", callback_query_id=cq["id"], text=label)
        except RuntimeError:
            pass  # la consulta pot haver caducat; l'estat ja està desat
        try:
            tg.call("editMessageReplyMarkup", chat_id=state["chat_id"], message_id=cq["message"]["message_id"],
                    reply_markup={"inline_keyboard": [[{"text": label, "callback_data": "noop|x|x"}]]})
        except RuntimeError:
            pass

    if changed:
        save_json(STATE_FILE, state)
    print(f"{len(updates)} actualitzacions processades")


if __name__ == "__main__":
    main()
