"""Manajemen state pengguna yang tersimpan di user_state.json."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

log = logging.getLogger("herosms-bot")

STATE_FILE = os.environ.get(
    "HEROSMS_STATE_FILE", os.path.join(os.path.dirname(__file__), "user_state.json")
)


def _load_state() -> Dict[int, Dict]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {int(k): v for k, v in raw.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(state: Dict[int, Dict]) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in state.items()}, f, ensure_ascii=False)
    except OSError as exc:
        log.warning("Gagal simpan state: %s", exc)


user_state: Dict[int, Dict] = _load_state()


def set_state(uid: int, key: str, val) -> None:
    user_state.setdefault(uid, {})[key] = val
    _save_state(user_state)


def get_state(uid: int, key: str, default=None):
    return user_state.get(uid, {}).get(key, default)


def clear_state(uid: int) -> None:
    user_state.pop(uid, None)
    _save_state(user_state)
