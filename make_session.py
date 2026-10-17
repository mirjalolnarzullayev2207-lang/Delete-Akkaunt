"""SESSION_STRING yaratadi (Render va boshqa diskisiz serverlar uchun).

Telefonda: GitHub Codespaces yoki Termux'da ishga tushiring:
    pip install telethon
    python make_session.py

API_ID va API_HASH so'raladi (yoki muhit o'zgaruvchilaridan olinadi), keyin
kanal admini akkauntining telefon raqami, Telegram'dan kelgan kod va (bo'lsa)
2FA paroli.

Qator session.txt fayliga yoziladi (terminaldan nusxalash xatoga olib keladi).
Faylni ochib, butun matnni nusxalang va Render'da SESSION_STRING sifatida saqlang.

DIQQAT: bu qator akkauntga to'liq kirish kalitidir. Hech kimga bermang,
GitHub'ga yuklamang va chatga tashlamang. Ishlatib bo'lgach session.txt ni o'chiring.
"""
import os

from telethon.sessions import StringSession
from telethon.sync import TelegramClient

api_id = int(os.getenv("API_ID") or input("API_ID: ").strip())
api_hash = os.getenv("API_HASH") or input("API_HASH: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    me = client.get_me()
    session_string = client.session.save()

print(f"\nKirildi: {me.first_name} (id={me.id})")

# Tekshiruv: qator yangi ulanishda haqiqatan ishlaydimi
with TelegramClient(StringSession(session_string), api_id, api_hash) as check:
    ok = check.get_me().id == me.id

with open("session.txt", "w", encoding="utf-8") as f:
    f.write(session_string)

print(f"Qator uzunligi: {len(session_string)} belgi (odatda 353)")
print("Tekshiruv:", "OK, qator ishlaydi" if ok else "XATO, qaytadan urinib ko'ring")
print("\nQator session.txt fayliga yozildi.")
print("Uni oching, butun matnni nusxalang va Render'ga SESSION_STRING qilib qo'ying.")
print("Ishlatib bo'lgach session.txt ni o'chiring.")
