"""Loyiha sozlamalari (.env faylidan o'qiladi)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f".env faylida {name} to'ldirilmagan")
    return value


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


@dataclass(frozen=True)
class Settings:
    api_id: int
    api_hash: str
    bot_token: str
    owner_ids: frozenset[int]
    channel: str | int
    session_name: str
    session_string: str
    threshold: int
    inactive_days: int
    burst_min: int
    kick_no_photo: bool
    daily_limit: int
    batch_size: int
    batch_pause: int
    data_dir: Path


def load_settings() -> Settings:
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)

    owners = frozenset(
        int(x) for x in _required("OWNER_IDS").replace(" ", "").split(",") if x
    )

    channel_raw = _required("CHANNEL")
    channel: str | int = (
        int(channel_raw) if channel_raw.lstrip("-").isdigit() else channel_raw
    )

    return Settings(
        api_id=int(_required("API_ID")),
        api_hash=_required("API_HASH"),
        bot_token=_required("BOT_TOKEN"),
        owner_ids=owners,
        channel=channel,
        session_name=os.getenv("SESSION_NAME", "cleaner_session"),
        session_string=os.getenv("SESSION_STRING", "").strip(),
        threshold=_int("THRESHOLD", 3),
        inactive_days=_int("INACTIVE_DAYS", 90),
        burst_min=_int("BURST_MIN", 15),
        kick_no_photo=os.getenv("KICK_NO_PHOTO", "").strip().lower()
        in ("1", "true", "yes", "ha"),
        daily_limit=_int("DAILY_LIMIT", 250),
        batch_size=_int("BATCH_SIZE", 30),
        batch_pause=_int("BATCH_PAUSE", 90),
        data_dir=data_dir,
    )
