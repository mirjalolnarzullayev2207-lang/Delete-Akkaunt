"""Asosiy mantiq: kanalni skanerlash va bosqichma-bosqich tozalash."""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Awaitable, Callable

from telethon import TelegramClient, errors
from telethon.tl.types import ChannelParticipantsAdmins, InputPeerUser

from analyzer import evaluate
from config import Settings
from storage import Storage

log = logging.getLogger(__name__)
Notify = Callable[[str], Awaitable[None]]


class CleanerService:
    def __init__(
        self, client: TelegramClient, settings: Settings, storage: Storage
    ) -> None:
        self.client = client
        self.s = settings
        self.storage = storage
        self.busy: str | None = None  # "scan" | "clean" | None
        self.last_scan: dict | None = None
        self._stop = asyncio.Event()

    def request_stop(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------
    async def scan(self, notify: Notify) -> None:
        self.busy = "scan"
        self._stop.clear()
        try:
            channel = await self.client.get_entity(self.s.channel)
            me = await self.client.get_me()

            protected = {me.id}
            async for admin in self.client.iter_participants(
                channel, filter=ChannelParticipantsAdmins
            ):
                protected.add(admin.id)

            already_removed = self.storage.removed_ids()
            now = datetime.now(timezone.utc)
            seen: set[int] = set()
            rows: list[tuple[int, str, int, str, int]] = []
            deleted_count = 0

            async for user in self.client.iter_participants(
                channel, aggressive=True
            ):
                if self._stop.is_set():
                    await notify("⏹ Skanerlash to'xtatildi (natija saqlanmadi).")
                    return
                if user.id in seen:
                    continue
                seen.add(user.id)

                if user.id in protected or user.id in already_removed or user.bot:
                    continue

                verdict = evaluate(user, now, self.s.inactive_days)
                if verdict.score >= self.s.threshold:
                    rows.append(
                        (
                            user.id,
                            user.username or "",
                            verdict.score,
                            ";".join(verdict.reasons),
                            user.access_hash or 0,
                        )
                    )
                    deleted_count += verdict.deleted

                if len(seen) % 2000 == 0:
                    await notify(f"⏳ {len(seen)} ta obunachi tekshirildi...")

            self.storage.replace_candidates(rows)
            self.last_scan = {
                "total": len(seen),
                "candidates": len(rows),
                "deleted": deleted_count,
                "at": now.strftime("%Y-%m-%d %H:%M UTC"),
            }
            await notify(
                "✅ Skanerlash tugadi\n"
                f"Ko'rilgan obunachilar: {len(seen)}\n"
                f"Nomzodlar: {len(rows)} (Deleted Account: {deleted_count})\n\n"
                "Telegram katta kanallarda ro'yxatni ~10 000 tagacha cheklaydi. "
                "Tozalagach yana skanerlang."
            )
        finally:
            self.busy = None

    # ------------------------------------------------------------------
    async def clean(self, notify: Notify) -> None:
        self.busy = "clean"
        self._stop.clear()
        kicked = 0
        try:
            left = self.s.daily_limit - self.storage.removed_today()
            if left <= 0:
                await notify(
                    f"Bugungi limit ({self.s.daily_limit}) to'lgan. Ertaga davom eting."
                )
                return

            rows = self.storage.pending(left)
            if not rows:
                await notify("O'chiriladigan nomzod yo'q. Avval skanerlang.")
                return

            channel = await self.client.get_entity(self.s.channel)
            await notify(f"🧹 Tozalash boshlandi: {len(rows)} ta akkaunt.")

            for user_id, username, _score, reasons, access_hash in rows:
                if self._stop.is_set():
                    await notify("⏹ Tozalash to'xtatildi.")
                    break

                # access_hash bazada saqlanadi, shuning uchun qayta ishga tushgandan
                # keyin ham (entity keshi bo'lmasa ham) akkauntni topish mumkin.
                peer = InputPeerUser(user_id, access_hash)
                result = await self._kick(channel, peer, notify)
                if result == "fatal":
                    break
                self.storage.mark_removed(user_id, username, reasons)
                if result == "ok":
                    kicked += 1

                if kicked and kicked % self.s.batch_size == 0 and result == "ok":
                    await notify(f"🧹 {kicked} ta chiqarildi, pauza...")
                    await asyncio.sleep(self.s.batch_pause + random.randint(0, 20))
                else:
                    await asyncio.sleep(random.uniform(2.0, 4.0))

            await notify(
                f"Tayyor: bu safar {kicked} ta akkaunt chiqarildi.\n"
                f"Qolgan nomzodlar: {self.storage.pending_count()}\n"
                f"Bugun jami: {self.storage.removed_today()}/{self.s.daily_limit}"
            )
        finally:
            self.busy = None

    # ------------------------------------------------------------------
    async def _kick(self, channel, peer: InputPeerUser, notify: Notify) -> str:
        """'ok' | 'skip' | 'fatal' qaytaradi."""
        user_id = peer.user_id
        while True:
            try:
                await self.client.kick_participant(channel, peer)
                return "ok"
            except errors.FloodWaitError as e:
                wait = e.seconds + 5
                log.warning("FloodWait %s soniya", wait)
                await notify(f"⏳ Telegram cheklovi: {wait} soniya kutaman...")
                await asyncio.sleep(wait)
            except (
                errors.ChatAdminRequiredError,
                errors.ChatAdminInviteRequiredError,
            ):
                await notify(
                    "❌ Akkauntda 'Obunachilarni cheklash' huquqi yo'q. To'xtatildi."
                )
                return "fatal"
            except (errors.UserAdminInvalidError, errors.UserNotParticipantError):
                return "skip"
            except Exception:
                log.exception("Kick xatosi: %s", user_id)
                return "skip"
