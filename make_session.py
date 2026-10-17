"""SESSION_STRING yaratadi (Render va boshqa diskisiz serverlar uchun).

Telefonda: GitHub Codespaces yoki Termux'da ishga tushiring:
    pip install telethon
    python make_session.py

API_ID va API_HASH so'raladi (yoki muhit o'zgaruvchilaridan olinadi), keyin
kanal admini akkauntining telefon raqami, Telegram'dan kelgan kod va (bo'lsa)
2FA paroli. Oxirida chiqqan uzun qatorni Render'da SESSION_STRING sifatida saqlang.

DIQQAT: bu qator akkauntga to'liq kirish kalitidir. Hech kimga bermang,
GitHub'ga yuklamang va chatga tashlamang.
"""
import os

from telethon.sessions import StringSession
from telethon.sync import TelegramClient

api_id = int(os.getenv("API_ID") or input("API_ID: ").strip())
api_hash = os.getenv("API_HASH") or input("API_HASH: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    me = client.get_me()
    print(f"\nKirildi: {me.first_name} (id={me.id})")
    print("\nQuyidagi qatorni SESSION_STRING sifatida saqlang:\n")
    print(client.session.save())
