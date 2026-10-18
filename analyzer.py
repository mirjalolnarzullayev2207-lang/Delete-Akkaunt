"""Akkauntni shubhalilik bo'yicha baholash (ball tizimi)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from telethon.tl.types import (
    User,
    UserStatusEmpty,
    UserStatusLastMonth,
    UserStatusLastWeek,
    UserStatusOffline,
)

FORCE = 50  # "majburiy" rejimlarda akkaunt o'z-o'zidan nomzod bo'lishi uchun ball


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
    burst_kick: bool = False,
    no_photo_kick: bool = False,
    inactive_kick: bool = False,
    include_lastweek: bool = False,
) -> Verdict:
    """Ball qancha baland bo'lsa, akkaunt shuncha shubhali.

    - Deleted Account                   -> darhol 100 ball
    - Avatar yo'q                       -> +1   (KICK_NO_PHOTO: +50)
    - Username yo'q                     -> +1
    - Telegram scam/fake                -> +3
    - Uzoq vaqt kirmagan                -> +2   (KICK_INACTIVE: +50)
    - Birdan ommaviy qo'shilgan (burst) -> +2   (KICK_BURST: +50)

    Telegram oxirgi kirishni aniq faqat foydalanuvchi ruxsat bergan bo'lsa beradi.
    Yashirganlar uchun faqat taxminiy oraliq: "yaqinda" (1-3 kun), "shu hafta"
    (3-7 kun), "shu oy" (7-30 kun), "uzoq vaqt oldin" (30+ kun).
    """
    if user.deleted:
        return Verdict(score=100, reasons=["deleted"], deleted=True)

    verdict = Verdict()

    if user.photo is None:
        verdict.score += 1
        verdict.reasons.append("avatar_yoq")
        if no_photo_kick:
            verdict.score += FORCE
            verdict.reasons.append("avatarsiz_majburiy")

    if not user.username:
        verdict.score += 1
        verdict.reasons.append("username_yoq")

    if getattr(user, "scam", False) or getattr(user, "fake", False):
        verdict.score += 3
        verdict.reasons.append("telegram_belgisi")

    inactive_reason = None
    status = user.status
    if status is None or isinstance(status, UserStatusEmpty):
        # 30+ kun kirmagan yoki hech qachon kirmagan
        inactive_reason = "uzoq_vaqt_kirmagan"
    elif isinstance(status, UserStatusOffline):
        was_online = status.was_online
        if was_online.tzinfo is None:
            was_online = was_online.replace(tzinfo=timezone.utc)
        if now - was_online > timedelta(days=inactive_days):
            inactive_reason = f"{inactive_days}_kundan_ortiq_kirmagan"
    elif isinstance(status, UserStatusLastMonth):
        # kamida 7 kun kirmagan (aniq)
        if inactive_days <= 7:
            inactive_reason = "kamida_7_kun_kirmagan"
    elif isinstance(status, UserStatusLastWeek):
        # 3-7 kun oldin kirgan (noaniq): faqat KICK_LASTWEEK yoqilgan bo'lsa
        if include_lastweek and inactive_days <= 7:
            inactive_reason = "3_7_kun_oldin_kirgan"

    if inactive_reason:
        verdict.score += 2
        verdict.reasons.append(inactive_reason)
        if inactive_kick:
            verdict.score += FORCE
            verdict.reasons.append("nofaol_majburiy")

    if burst:
        verdict.score += 2
        verdict.reasons.append("birdan_ommaviy_qoshilgan")
        if burst_kick:
            verdict.score += FORCE
            verdict.reasons.append("ommaviy_majburiy")

    return verdict
