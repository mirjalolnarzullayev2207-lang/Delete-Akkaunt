# Telegram Kanal Tozalagich

Kanaldagi nakrutka/bot obunachilarni (Deleted Account, avatarsiz, username'siz, uzoq vaqt kirmagan) aniqlaydi va **kuniga limit bilan, bosqichma-bosqich** kanaldan chiqaradi. Boshqaruv Telegram'dagi bot orqali, tugmalar bilan.

## Qanday ishlaydi
Telegram botlarga obunachilar ro'yxatini bermaydi, shuning uchun loyiha ikki qismdan iborat:
- **Userbot (Telethon)**: kanal admini akkaunti nomidan skanerlaydi va chiqaradi.
- **Boshqaruv boti (aiogram)**: faqat egasi (`OWNER_IDS`) tugmalar orqali boshqaradi.

## Talablar
- Python 3.10+ (yoki Docker)
- Kanalda admin bo'lgan akkaunt, "Obunachilarni cheklash" huquqi bilan
- `API_ID`/`API_HASH` (https://my.telegram.org -> API development tools)
- @BotFather dan bot tokeni

## O'rnatish
```bash
git clone <repo-manzili> && cd <papka>
cp .env.example .env        # va ichini to'ldiring
pip install -r requirements.txt
python login.py             # bir marta: telefon + kod
python bot.py
```

### Docker bilan (server uchun tavsiya)
```bash
cp .env.example .env        # to'ldiring
docker compose run --rm cleaner python login.py   # bir marta
docker compose up -d --build
docker compose logs -f
```

## Ishlatish
Botga `/start` yuboring:
1. **Skanerlash**: obunachilar tahlil qilinadi, hech kim o'chirilmaydi.
2. **Hisobot**: nomzodlar CSV faylini oling va tekshiring.
3. **Tozalashni boshlash**: tasdiqlagach kuniga `DAILY_LIMIT` gacha chiqaradi.
4. **To'xtatish** va **Holat** tugmalari istalgan vaqtda ishlaydi.

Taxminan 7-8 ming akkaunt uchun 3-4 hafta: har kuni "Tozalashni boshlash" ni bosing.

## Ball tizimi
| Belgi | Ball |
|---|---|
| Deleted Account | darhol o'chiriladi |
| Avatar yo'q | +1 |
| Username yo'q | +1 |
| Telegram scam/fake belgisi | +3 |
| Uzoq vaqt kirmagan | +2 |

Standart chegara: 3 ball. Ehtiyotkorroq bo'lish uchun `THRESHOLD=4`.

## Muhim
- `data/` papkasi va `.session` fayli akkauntga kirish kalitidir. Hech kimga bermang va GitHub'ga yuklamang (`.gitignore` da bor).
- Telegram katta kanallarda ro'yxatni ~10 000 tagacha cheklaydi, tozalagach qayta skanerlang.
- Chiqarilgan odam havola orqali qaytib kira oladi (ban qilinmaydi).
- Avatarsiz va username'siz haqiqiy, faol bo'lmagan obunachilar ham nomzod bo'lishi mumkin. O'chirishdan oldin hisobotni tekshiring.
