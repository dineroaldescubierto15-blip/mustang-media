"""Funcions compartides: fitxers d'estat, Telegram i rutes."""
import datetime as dt
import json
import os
from zoneinfo import ZoneInfo
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES_DIR = ROOT / "data" / "candidates"
STATE_FILE = ROOT / "data" / "telegram_state.json"
HISTORY_FILE = ROOT / "data" / "history.json"
CONFIG_FILE = ROOT / "config" / "sources.json"
UTC = dt.timezone.utc


def load_json(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def now_utc() -> dt.datetime:
    return dt.datetime.now(UTC)


def raw_url(media_path: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "dineroaldescubierto15-blip/mustang-media")
    return f"https://raw.githubusercontent.com/{repo}/main/{media_path}"


class Telegram:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"

    def call(self, method: str, files=None, **params):
        if files:
            data = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items()}
            r = requests.post(f"{self.base}/{method}", data=data, files=files, timeout=300)
        else:
            r = requests.post(f"{self.base}/{method}", json=params, timeout=60)
        body = r.json()
        if not body.get("ok"):
            raise RuntimeError(f"Telegram {method}: {body.get('description')}")
        return body["result"]


def chat_id() -> int | None:
    env = os.environ.get("TELEGRAM_CHAT_ID")
    if env:
        return int(env)
    return load_json(STATE_FILE, {}).get("chat_id")


# ---------- Missatges de Telegram ----------

STATUS_LABEL = {
    "pending": "⏳ Pendent d'aprovar",
    "approved": "✅ APROVAT · a la cua per publicar",
    "rejected": "❌ DESCARTAT",
    "published": "📣 PUBLICAT",
}


def title(c: dict) -> str:
    """Nom curt del candidat: tipus, autor i l'inici del text original."""
    kind = "Reel" if c["media_type"] == "REELS" else "Post"
    first = (c.get("original_caption") or "").strip().splitlines()
    snippet = first[0][:45].strip() if first else ""
    return f"{kind} de @{c['author']}" + (f" · «{snippet}»" if snippet else "")


def header(c: dict) -> str:
    views = f" · 👁 {c['views']:,}" if c.get("views") else ""
    return (
        f"🐎 {title(c)}\n"
        f"❤️ {c['likes']:,} · 💬 {c['comments']:,}{views} · fa {c['age_hours']:.0f} h\n"
        f"🔗 {c['original_url']}\n\n"
        f"{STATUS_LABEL.get(c.get('status', 'pending'), '')}"
    )[:1024]


def mark_message(tg: "Telegram", chat: int, c: dict) -> None:
    """Treu els botons i deixa escrit l'estat al missatge del candidat."""
    if not c.get("message_id"):
        return
    try:
        method = "editMessageText" if c.get("message_kind") == "text" else "editMessageCaption"
        field = "text" if method == "editMessageText" else "caption"
        tg.call(method, chat_id=chat, message_id=c["message_id"], **{field: header(c)},
                reply_markup={"inline_keyboard": []})
    except RuntimeError as e:
        if "not modified" not in str(e):
            print(f"No s'ha pogut actualitzar el missatge de {c['shortCode']}: {e}")


def iter_candidates(max_days: int = 5):
    """Candidats recents: (fitxer, dades, candidat)."""
    cutoff = (now_utc() - dt.timedelta(days=max_days)).date().isoformat()
    for path in sorted(CANDIDATES_DIR.glob("*.json")):
        if path.stem < cutoff:
            continue
        data = load_json(path, {"candidates": []})
        for c in data["candidates"]:
            yield path, data, c


def queue_text(config: dict) -> str:
    approved, pending = [], []
    for _, _, c in iter_candidates():
        if c.get("status") == "approved":
            approved.append(c)
        elif c.get("status", "pending") == "pending" and c.get("message_id"):
            pending.append(c)
    approved.sort(key=lambda c: c.get("decided_at", ""))

    def section(items, empty):
        reels = [c for c in items if c["media_type"] == "REELS"]
        posts = [c for c in items if c["media_type"] != "REELS"]
        lines = []
        for name, group in (("🎬 Reels", reels), ("🖼 Posts", posts)):
            lines.append(f"{name} ({len(group)})")
            lines += [f"  {i}. {title(c)}" for i, c in enumerate(group, 1)] or ["  —"]
        return "\n".join(lines) if items else f"  {empty}"

    times = " i ".join(config.get("publish_times", []))
    return (
        f"📋 CUA DE @{config.get('account', 'mustangemotion')}\n"
        f"Actualitzat: {now_utc().astimezone(ZoneInfo('Europe/Madrid')):%d/%m %H:%M} (Manresa)\n\n"
        f"✅ Aprovats, per ordre de publicació ({len(approved)}):\n{section(approved, "Cap. No es publicarà res fins que n'aprovis algun.")}\n\n"
        f"⏳ Pendents d'aprovar ({len(pending)}):\n{section(pending, 'Cap.')}\n\n"
        f"🕐 Es publica a les {times} (Nova York)."
    )[:4096]


def update_pinned(tg: "Telegram", state: dict, config: dict) -> None:
    """Manté un missatge fixat al xat amb la cua de pendents i aprovats."""
    chat = state.get("chat_id")
    if not chat:
        return
    text = queue_text(config)
    if state.get("pinned_text") == text.split("\n", 2)[2]:
        return  # res no ha canviat (ignorem la línia de l'hora)
    try:
        if state.get("pinned_message_id"):
            tg.call("editMessageText", chat_id=chat, message_id=state["pinned_message_id"], text=text)
        else:
            raise RuntimeError("sense missatge fixat")
    except RuntimeError as e:
        if "not modified" in str(e):
            return
        msg = tg.call("sendMessage", chat_id=chat, text=text, disable_notification=True)
        state["pinned_message_id"] = msg["message_id"]
        try:
            tg.call("pinChatMessage", chat_id=chat, message_id=msg["message_id"], disable_notification=True)
        except RuntimeError as pin_err:
            print(f"No s'ha pogut fixar el missatge: {pin_err}")
    state["pinned_text"] = text.split("\n", 2)[2]


def sync_drafts(tg: "Telegram", chat: int) -> None:
    """Envia o actualitza l'esborrany de descripció dels candidats pendents/aprovats si ha canviat."""
    for path, data, c in iter_candidates():
        if c.get("status", "pending") not in ("pending", "approved") or not c.get("message_id"):
            continue
        if c.get("caption_sent") == c["caption"]:
            continue
        text = f"📝 Esborrany de la descripció:\n\n{c['caption']}"
        try:
            if c.get("caption_message_id"):
                tg.call("editMessageText", chat_id=chat, message_id=c["caption_message_id"], text=text)
            else:
                msg = tg.call("sendMessage", chat_id=chat, reply_to_message_id=c["message_id"], text=text,
                              disable_notification=True)
                c["caption_message_id"] = msg["message_id"]
        except RuntimeError as e:
            if "not modified" not in str(e):
                print(f"No s'ha pogut actualitzar l'esborrany de {c['shortCode']}: {e}")
                continue
        c["caption_sent"] = c["caption"]
        save_json(path, data)
