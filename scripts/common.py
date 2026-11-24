"""Funcions compartides: fitxers d'estat, Telegram i rutes."""
import datetime as dt
import json
import os
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
