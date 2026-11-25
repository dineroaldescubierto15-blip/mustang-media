#!/usr/bin/env python3
"""Diagnòstic del bot: webhook actiu i actualitzacions pendents (sense confirmar-ne cap)."""
import json, os, requests
base = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}"
me = requests.get(f"{base}/getMe", timeout=30).json()
print("bot:", me.get("result", {}).get("username"))
wh = requests.get(f"{base}/getWebhookInfo", timeout=30).json()
print("webhook:", json.dumps(wh.get("result"), ensure_ascii=False))
up = requests.get(f"{base}/getUpdates", params={"timeout": 0, "limit": 100,
                  "allowed_updates": json.dumps(["message", "callback_query"])}, timeout=30).json()
print("getUpdates ok:", up.get("ok"), up.get("description"))
for u in up.get("result", []):
    kind = "callback" if "callback_query" in u else "message"
    data = u.get("callback_query", {}).get("data") or u.get("message", {}).get("text")
    print(" ", u["update_id"], kind, data)
print("state offset:", json.load(open("data/telegram_state.json")).get("offset"))
