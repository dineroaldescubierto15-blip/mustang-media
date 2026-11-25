#!/usr/bin/env python3
"""Connecta el bot de Telegram al webhook de Make (o el desconnecta amb MODE=delete)."""
import os

from common import Telegram

tg = Telegram(os.environ["TELEGRAM_BOT_TOKEN"])
if os.environ.get("MODE") == "delete":
    tg.call("deleteWebhook", drop_pending_updates=False)
    print("Webhook eliminat: el bot torna al mode de lectura periòdica")
else:
    tg.call("setWebhook", url=os.environ["MAKE_WEBHOOK_URL"], allowed_updates=["message", "callback_query"],
            drop_pending_updates=False)
    print("Webhook configurat:", tg.call("getWebhookInfo").get("url", "")[:40] + "…")
