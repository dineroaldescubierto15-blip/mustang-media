#!/usr/bin/env python3
"""Si és hora de publicar (franges de config, hora de Nova York), envia a Make el candidat aprovat més antic.

Make publica a Instagram i respon amb l'ID del post. Cada franja només es processa un cop al dia,
encara que GitHub Actions s'endarrereixi (es publica fins a 90 minuts després de l'hora prevista).
"""
import datetime as dt
import os
from zoneinfo import ZoneInfo

import requests

from common import (CANDIDATES_DIR, CONFIG_FILE, HISTORY_FILE, STATE_FILE, Telegram, load_json, mark_message,
                    now_utc, raw_url, save_json, title, update_pinned)

LATE_WINDOW = dt.timedelta(minutes=90)
MAX_QUEUE_AGE = dt.timedelta(days=4)


def due_slot(config: dict, state: dict) -> str | None:
    tz = ZoneInfo(config.get("timezone", "America/New_York"))
    local = now_utc().astimezone(tz)
    done = state.get("slots_done", [])
    for hhmm in config["publish_times"]:
        h, m = map(int, hhmm.split(":"))
        target = local.replace(hour=h, minute=m, second=0, microsecond=0)
        key = f"{local.date()} {hhmm}"
        if target <= local < target + LATE_WINDOW and key not in done:
            return key
    return None


def next_approved():
    best = None
    for path in sorted(CANDIDATES_DIR.glob("*.json")):
        data = load_json(path, {"candidates": []})
        for c in data["candidates"]:
            if c.get("status") != "approved":
                continue
            decided = dt.datetime.fromisoformat(c.get("decided_at", now_utc().isoformat()))
            if now_utc() - decided > MAX_QUEUE_AGE:
                continue
            if best is None or decided < best[2]:
                best = (path, c["shortCode"], decided)
    return best


def main() -> None:
    config, state = load_json(CONFIG_FILE, {}), load_json(STATE_FILE, {})
    if os.environ.get("FORCE_PUBLISH") == "true":
        slot = f"manual {now_utc():%Y-%m-%d %H:%M}"  # publicació demanada a mà, fora de franja
    else:
        slot = due_slot(config, state)
    if not slot:
        print("No és hora de publicar")
        return

    token, webhook = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("MAKE_WEBHOOK_URL")
    tg = Telegram(token) if token and state.get("chat_id") else None

    def notify(text: str) -> None:
        if tg:
            tg.call("sendMessage", chat_id=state["chat_id"], text=text, disable_web_page_preview=True)

    if not webhook:
        print("Encara no hi ha MAKE_WEBHOOK_URL; no es publica")
        return

    state.setdefault("slots_done", []).append(slot)
    state["slots_done"] = state["slots_done"][-20:]
    save_json(STATE_FILE, state)

    pick = next_approved()
    if not pick:
        notify(f"🚫 Franja {slot.split()[1]} (Nova York): no s'ha publicat res perquè no hi havia cap candidat aprovat.")
        return

    path, code, _ = pick
    data = load_json(path, {"candidates": []})
    c = next(x for x in data["candidates"] if x["shortCode"] == code)
    payload = {"media_type": c["media_type"], "media_url": raw_url(c["media_path"]),
               "caption": c["caption"], "author": c["author"], "shortCode": code}
    r_text_accepted = False
    try:
        r = requests.post(webhook, json=payload, timeout=300)
        r_text_accepted = r.status_code == 200 and r.text.strip() == "Accepted"
        # Només és èxit si l'escenari de Make ha respost {"ok": true}. Un "Accepted" vol dir que
        # l'escenari està aturat i la petició s'ha quedat a la cua del webhook sense publicar.
        ok = r.status_code == 200 and '"ok": true' in r.text.replace('"ok":true', '"ok": true')
        if r.text.strip() == "Accepted":
            detail = ("Make ha rebut la petició però l'escenari no l'ha processat: comprova que l'escenari "
                      "de Make estigui ACTIVAT.")
        else:
            detail = r.text[:200]
    except requests.RequestException as e:
        ok, detail = False, str(e)

    if r_text_accepted:
        # Make ha guardat la petició a la seva cua i la publicarà més tard: NO es pot tornar a enviar,
        # o el post sortiria repetit. Es marca com a enviat i es demana comprovar-ho.
        c["status"] = "published"
        c["published_at"] = now_utc().isoformat()
        c["publish_unconfirmed"] = True
        save_json(path, data)
        history = load_json(HISTORY_FILE, {"published": []})
        history["published"].append({"shortCode": code, "author": c["author"], "published_at": c["published_at"],
                                     "original_url": c["original_url"], "caption_style": c.get("caption_style"),
                                     "unconfirmed": True})
        save_json(HISTORY_FILE, history)
        notify(f"⚠️ {title(c)}: Make ha rebut la publicació però no l'ha confirmada (l'escenari no és en mode "
               f"immediat). Es publicarà quan Make la processi; no es tornarà a enviar. Comprova que surti un sol cop.")
        return

    if not ok:
        notify(f"⚠️ No s'ha pogut publicar: {title(c)}. Continua aprovat i es tornarà a provar a la "
               f"propera franja.\nDetall: {detail}")
        return

    c["status"] = "published"
    c["published_at"] = now_utc().isoformat()
    save_json(path, data)
    history = load_json(HISTORY_FILE, {"published": []})
    history["published"].append({"shortCode": code, "author": c["author"], "published_at": c["published_at"],
                                 "original_url": c["original_url"],
                                 "caption_style": c.get("caption_style")})
    save_json(HISTORY_FILE, history)
    notify(f"📣 Publicat: {title(c)}\nhttps://www.instagram.com/{config['account']}/\n\n"
           f"📝 Descripció publicada:\n{c['caption']}")
    if config.get("tiktok", {}).get("enabled") and not c.get("tiktok_post_id"):
        try:  # TikTok mai bloqueja Instagram: si falla, s'avisa i prou
            import tiktok
            c["tiktok_post_id"] = tiktok.publish_candidate(c, config) or "ok"
            c["tiktok_published_at"] = now_utc().isoformat()
            save_json(path, data)
            notify(f"🎵 També publicat a TikTok: {title(c)}")
        except Exception as e:  # noqa: BLE001
            c["tiktok_error"] = str(e)[:300]
            save_json(path, data)
            notify(f"⚠️ No s'ha pogut publicar a TikTok: {title(c)}\nDetall: {str(e)[:200]}")
    if tg:
        mark_message(tg, state["chat_id"], c)
        update_pinned(tg, state, config)
        save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
