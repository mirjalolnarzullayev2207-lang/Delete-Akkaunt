"""Boshqaruv boti (aiogram 3). Ishga tushirish: python bot.py"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from telethon import TelegramClient
from telethon.sessions import StringSession

from config import Settings, load_settings
from service import CleanerService
from storage import Storage

log = logging.getLogger("bot")


def menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Skanerlash", callback_data="scan"),
                InlineKeyboardButton(text="📄 Hisobot", callback_data="report"),
            ],
            [InlineKeyboardButton(text="🧹 Tozalashni boshlash", callback_data="clean")],
            [
                InlineKeyboardButton(text="⏹ To'xtatish", callback_data="stop"),
                InlineKeyboardButton(text="📊 Holat", callback_data="status"),
            ],
        ]
    )


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, boshlash", callback_data="clean_yes"),
                InlineKeyboardButton(text="❌ Bekor", callback_data="cancel"),
            ]
        ]
    )


def build_router(
    settings: Settings, service: CleanerService, storage: Storage, bot: Bot
) -> Router:
    router = Router()
    owners = set(settings.owner_ids)
    # Faqat egasi (OWNER_IDS) botdan foydalana oladi
    router.message.filter(F.from_user.id.in_(owners))
    router.callback_query.filter(F.from_user.id.in_(owners))

    tasks: set[asyncio.Task] = set()

    def spawn(job, chat_id: int) -> None:
        async def notify(text: str) -> None:
            try:
                await bot.send_message(chat_id, text)
            except Exception:
                log.exception("Xabar yuborilmadi")

        async def runner() -> None:
            try:
                await job(notify)
            except Exception as e:  # noqa: BLE001
                log.exception("Vazifa xatosi")
                await notify(f"❌ Xatolik: {e}")

        task = asyncio.create_task(runner())
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    def status_text() -> str:
        last = service.last_scan
        scan_line = (
            f"{last['at']}: {last['total']} ta ko'rildi, {last['candidates']} nomzod"
            if last
            else "hali skanerlanmagan"
        )
        return (
            "📊 Holat\n"
            f"Jarayon: {service.busy or 'bo`sh'}\n"
            f"Oxirgi skan: {scan_line}\n"
            f"Kutayotgan nomzodlar: {storage.pending_count()}\n"
            f"Bugun o'chirilgan: {storage.removed_today()}/{settings.daily_limit}\n"
            f"Jami o'chirilgan: {storage.removed_total()}"
        )

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        await message.answer(
            "Kanal tozalagich. Tartib: 1) Skanerlash, 2) Hisobotni ko'rish, "
            "3) Tozalashni boshlash.",
            reply_markup=menu_kb(),
        )

    @router.message(Command("status"))
    async def status_cmd(message: Message) -> None:
        await message.answer(status_text(), reply_markup=menu_kb())

    @router.callback_query(F.data == "status")
    async def status_cb(call: CallbackQuery) -> None:
        await call.answer()
        await call.message.answer(status_text(), reply_markup=menu_kb())

    @router.callback_query(F.data == "scan")
    async def scan_cb(call: CallbackQuery) -> None:
        if service.busy:
            await call.answer(f"Band: {service.busy}", show_alert=True)
            return
        await call.answer()
        await call.message.answer("🔍 Skanerlash boshlandi. Bir necha daqiqa ketadi.")
        spawn(service.scan, call.message.chat.id)

    @router.callback_query(F.data == "report")
    async def report_cb(call: CallbackQuery) -> None:
        path = settings.data_dir / "candidates.csv"
        count = storage.export_candidates_csv(path)
        if not count:
            await call.answer("Nomzod yo'q. Avval skanerlang.", show_alert=True)
            return
        await call.answer()
        await call.message.answer_document(
            FSInputFile(path), caption=f"Nomzodlar: {count} ta"
        )

    @router.callback_query(F.data == "clean")
    async def clean_cb(call: CallbackQuery) -> None:
        if service.busy:
            await call.answer(f"Band: {service.busy}", show_alert=True)
            return
        pending = storage.pending_count()
        if not pending:
            await call.answer("Nomzod yo'q. Avval skanerlang.", show_alert=True)
            return
        await call.answer()
        left = max(settings.daily_limit - storage.removed_today(), 0)
        await call.message.answer(
            f"Kutayotgan nomzodlar: {pending}\n"
            f"Bugun yana o'chirish mumkin: {left}\n\n"
            "Hisobotni tekshirdingizmi? Boshlaymizmi?",
            reply_markup=confirm_kb(),
        )

    @router.callback_query(F.data == "clean_yes")
    async def clean_yes_cb(call: CallbackQuery) -> None:
        if service.busy:
            await call.answer(f"Band: {service.busy}", show_alert=True)
            return
        await call.answer()
        spawn(service.clean, call.message.chat.id)

    @router.callback_query(F.data == "cancel")
    async def cancel_cb(call: CallbackQuery) -> None:
        await call.answer("Bekor qilindi")

    @router.callback_query(F.data == "stop")
    async def stop_cb(call: CallbackQuery) -> None:
        if not service.busy:
            await call.answer("Hozir hech narsa ishlamayapti.", show_alert=True)
            return
        service.request_stop()
        await call.answer("To'xtatish so'raldi...")

    return router


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = load_settings()

    # SESSION_STRING berilgan bo'lsa (Render kabi diskisiz serverlar uchun) shuni
    # ishlatamiz, aks holda data/ ichidagi .session fayldan foydalanamiz.
    session = (
        StringSession(settings.session_string)
        if settings.session_string
        else str(settings.data_dir / settings.session_name)
    )
    client = TelegramClient(session, settings.api_id, settings.api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit(
            "Akkaunt kirmagan. `python make_session.py` bilan SESSION_STRING oling "
            "yoki `python login.py` ni ishga tushiring."
        )

    storage = Storage(settings.data_dir / "cleaner.db")
    service = CleanerService(client, settings, storage)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(build_router(settings, service, storage, bot))

    log.info("Bot ishga tushdi")
    try:
        await dp.start_polling(bot)
    finally:
        await client.disconnect()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
