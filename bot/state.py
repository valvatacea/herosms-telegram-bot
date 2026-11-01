"""Manajemen state pengguna yang tersimpan di user_state.json."""
from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:  # pragma: no cover - non-Linux
    HAS_FCNTL = False

log = logging.getLogger("herosms-bot")

STATE_FILE = os.environ.get(
    "HEROSMS_STATE_FILE", os.path.join(os.path.dirname(__file__), "user_state.json")
)
LOCK_FILE = STATE_FILE + ".lock"


if HAS_FCNTL:
    _fcntl = fcntl
else:  # pragma: no cover - non-Linux
    _fcntl = None

@contextmanager
def _locked():
    """Kunci file state selama operasi baca-tulis (mencegah race condition multi-instance)."""
    if not HAS_FCNTL:
        yield
        return
    lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        _fcntl.flock(lock_fd, _fcntl.LOCK_EX)
        yield
    finally:
        _fcntl.flock(lock_fd, _fcntl.LOCK_UN)
        os.close(lock_fd)


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
    with _locked():
        state = _load_state()  # muat ulang dari disk untuk capture perubahan instance lain
        state.setdefault(uid, {})[key] = val
        _save_state(state)
        user_state.update(state)


def get_state(uid: int, key: str, default=None):
    return user_state.get(uid, {}).get(key, default)


def clear_state(uid: int) -> None:
    with _locked():
        state = _load_state()
        state.pop(uid, None)
        _save_state(state)
        user_state.clear()      # hapus kunti lama agar sinkron dengan disk
        user_state.update(state)
