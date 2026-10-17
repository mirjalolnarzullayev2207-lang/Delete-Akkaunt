"""Akkauntni shubhalilik bo'yicha baholash (ball tizimi)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from telethon.tl.types import User, UserStatusEmpty, UserStatusOffline


@dataclass
class Verdict:
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    deleted: bool = False


def evaluate(user: User, now: datetime, inactive_days: int) -> Verdict:
    """Ball qancha baland bo'lsa, akkaunt shuncha shubhali.

    - Deleted Account         -> darhol 100 ball
    - Avatar yo'q             -> +1
    - Username yo'q           -> +1
    - Telegram scam/fake      -> +3
    - Uzoq vaqt kirmagan      -> +2
    """
    if user.deleted:
        return Verdict(score=100, reasons=["deleted"], deleted=True)

    verdict = Verdict()

    if user.photo is None:
        verdict.score += 1
        verdict.reasons.append("avatar_yoq")

    if not user.username:
        verdict.score += 1
        verdict.reasons.append("username_yoq")

    if getattr(user, "scam", False) or getattr(user, "fake", False):
        verdict.score += 3
        verdict.reasons.append("telegram_belgisi")

    status = user.status
    if status is None or isinstance(status, UserStatusEmpty):
        # Telegram 1 oydan ko'p kirmagan akkauntlarga shunday status beradi
        verdict.score += 2
        verdict.reasons.append("uzoq_vaqt_kirmagan")
    elif isinstance(status, UserStatusOffline):
        was_online = status.was_online
        if was_online.tzinfo is None:
            was_online = was_online.replace(tzinfo=timezone.utc)
        if now - was_online > timedelta(days=inactive_days):
            verdict.score += 2
            verdict.reasons.append(f"{inactive_days}_kundan_ortiq_kirmagan")

    return verdict
