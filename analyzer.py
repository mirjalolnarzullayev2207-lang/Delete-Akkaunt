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


def _join_date(user: User) -> datetime | None:
    """Obunachi kanalga qo'shilgan vaqt (Telethon user.participant.date)."""
    participant = getattr(user, "participant", None)
    date = getattr(participant, "date", None)
    if date is None:
        return None
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return date


def find_burst_ids(users, min_count: int, window_min: int = 10) -> set[int]:
    """Qisqa vaqt ichida ommaviy qo'shilgan akkauntlar (nakrutka belgisi).

    `window_min` daqiqalik oynada kamida `min_count` kishi qo'shilgan bo'lsa,
    shu oynadagi hamma burst hisoblanadi. min_count <= 0 bo'lsa o'chiriladi.
    """
    if min_count <= 0:
        return set()
    size = window_min * 60
    buckets: dict[tuple[int, int], list[int]] = {}
    for u in users:
        d = _join_date(u)
        if d is None:
            continue
        ts = int(d.timestamp())
        # ikkita siljitilgan oyna: oyna chegarasida bo'linib ketmasligi uchun
        for shift, offset in ((0, 0), (1, size // 2)):
            buckets.setdefault((shift, (ts + offset) // size), []).append(u.id)
    burst: set[int] = set()
    for ids in buckets.values():
        if len(ids) >= min_count:
            burst.update(ids)
    return burst


def evaluate(
    user: User,
    now: datetime,
    inactive_days: int,
    burst: bool = False,
    no_photo_kick: bool = False,
) -> Verdict:
    """Ball qancha baland bo'lsa, akkaunt shuncha shubhali.

    - Deleted Account         -> darhol 100 ball
    - Avatar yo'q             -> +1
    - Username yo'q           -> +1
    - Telegram scam/fake      -> +3
    - Uzoq vaqt kirmagan      -> +2
    - Birdan ommaviy qo'shilgan (burst) -> +2
    """
    if user.deleted:
        return Verdict(score=100, reasons=["deleted"], deleted=True)

    verdict = Verdict()

    if user.photo is None:
        verdict.score += 1
        verdict.reasons.append("avatar_yoq")
        if no_photo_kick:
            # KICK_NO_PHOTO yoqilgan: avatarsiz akkaunt o'z-o'zidan nomzod
            verdict.score += 50
            verdict.reasons.append("avatarsiz_majburiy")

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

    if burst:
        verdict.score += 2
        verdict.reasons.append("birdan_ommaviy_qoshilgan")

    return verdict
