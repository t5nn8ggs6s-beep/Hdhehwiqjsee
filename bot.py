import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = "8448082383:AAGrcma1oAyLrKUlZFMsLT5-ltgs_DPWxW8"
ADMIN_ID = 8146320391

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= БАЗА =================
db = sqlite3.connect("novpnniffy.db")
sql = db.cursor()

sql.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    referrer INTEGER,
    key TEXT
)
""")

sql.execute("""
CREATE TABLE IF NOT EXISTS keys(
    code TEXT PRIMARY KEY,
    used INTEGER DEFAULT 0
)
""")

sql.execute("""
CREATE TABLE IF NOT EXISTS reviews(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT,
    rating INTEGER
)
""")

db.commit()

# ---------- Генерация 50 ключей ----------
sql.execute("SELECT COUNT(*) FROM keys")
if sql.fetchone()[0] == 0:
    codes = set()
    while len(codes) < 50:
        codes.add(str(random.randint(100000000, 999999999)))
    for c in codes:
        sql.execute("INSERT INTO keys(code) VALUES(?)", (c,))
    db.commit()

# ================= КНОПКИ =================

main_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add("🛒 Получить VPN", "👤 Мой ключ")
main_kb.add("🎁 Рефералка", "⭐ Отзывы")
main_kb.add("ℹ️ Инструкция")

admin_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
admin_kb.add("📊 Статистика", "📨 Рассылка")

# ================= СТАРТ =================
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):

    args = msg.get_args()
    ref = int(args) if args.isdigit() else None

    sql.execute("SELECT * FROM users WHERE user_id=?", (msg.from_user.id,))
    if not sql.fetchone():
        sql.execute(
            "INSERT INTO users(user_id, referrer) VALUES(?, ?)",
            (msg.from_user.id, ref)
        )
        db.commit()

    await msg.answer(
        "🔐 NO VPNNiffy — бесплатный VPN магазин\n\n"
        "Выберите действие:",
        reply_markup=main_kb
    )

# ================= ВЫДАЧА VPN =================
@dp.message_handler(lambda m: m.text == "🛒 Получить VPN")
async def get_vpn(msg: types.Message):

    sql.execute("SELECT key FROM users WHERE user_id=?", (msg.from_user.id,))
    if sql.fetchone()[0]:
        await msg.answer("❗ У вас уже есть ключ")
        return

    sql.execute("SELECT code FROM keys WHERE used=0")
    row = sql.fetchone()

    if not row:
        await msg.answer("❌ Ключи закончились")
        return

    code = row[0]

    sql.execute("UPDATE keys SET used=1 WHERE code=?", (code,))
    sql.execute("UPDATE users SET key=? WHERE user_id=?", (code, msg.from_user.id))
    db.commit()

    await msg.answer(
        f"🎉 Ваш код доступа:\n\n🔑 {code}\n\n"
        f"📱 Скачайте VPNIFY в Play Market или App Store\n\n"
        f"📖 Инструкция:\n"
        f"1. Установите приложение\n"
        f"2. Откройте его\n"
        f"3. Введите код\n"
        f"4. Подключитесь\n\n"
        f"✅ Приятного пользования 🚀"
    )

# ================= МОЙ КЛЮЧ =================
@dp.message_handler(lambda m: m.text == "👤 Мой ключ")
async def my_key(msg: types.Message):
    sql.execute("SELECT key FROM users WHERE user_id=?", (msg.from_user.id,))
    key = sql.fetchone()[0]

    if key:
        await msg.answer(f"🔑 Ваш ключ:\n{key}")
    else:
        await msg.answer("❌ У вас нет ключа")

# ================= РЕФЕРАЛКА =================
@dp.message_handler(lambda m: m.text == "🎁 Рефералка")
async def referral(msg: types.Message):
    link = f"https://t.me/{(await bot.get_me()).username}?start={msg.from_user.id}"

    sql.execute("SELECT COUNT(*) FROM users WHERE referrer=?", (msg.from_user.id,))
    refs = sql.fetchone()[0]

    await msg.answer(
        f"🎁 Ваша ссылка:\n{link}\n\n👥 Приглашено: {refs}"
    )

# ================= ИНСТРУКЦИЯ =================
@dp.message_handler(lambda m: m.text == "ℹ️ Инструкция")
async def instruction(msg: types.Message):
    await msg.answer(
        "📱 Как подключиться:\n\n"
        "1. Скачайте VPNIFY\n"
        "2. Откройте приложение\n"
        "3. Введите ваш код\n"
        "4. Нажмите подключиться"
    )

# ================= ОТЗЫВЫ =================
waiting_review = {}

@dp.message_handler(lambda m: m.text == "⭐ Отзывы")
async def review_start(msg: types.Message):
    waiting_review[msg.from_user.id] = "text"
    await msg.answer("✍️ Напишите ваш отзыв:")

@dp.message_handler()
async def review_process(msg: types.Message):

    if waiting_review.get(msg.from_user.id) == "text":
        waiting_review[msg.from_user.id] = msg.text
        await msg.answer("⭐ Оцените от 1 до 5")
        return

    if isinstance(waiting_review.get(msg.from_user.id), str):
        try:
            rating = int(msg.text)
            if rating < 1 or rating > 5:
                raise ValueError
        except:
            await msg.answer("Введите число от 1 до 5")
            return

        text = waiting_review[msg.from_user.id]

        sql.execute(
            "INSERT INTO reviews(user_id, text, rating) VALUES(?,?,?)",
            (msg.from_user.id, text, rating)
        )
        db.commit()

        waiting_review.pop(msg.from_user.id)

        await msg.answer("✅ Спасибо за отзыв 💚")

        await bot.send_message(
            ADMIN_ID,
            f"📝 Новый отзыв\n\n👤 {msg.from_user.id}\n⭐ {rating}\n💬 {text}"
        )

# ================= АДМИН ПАНЕЛЬ =================
@dp.message_handler(commands=["admin"])
async def admin_panel(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("👑 Админ панель", reply_markup=admin_kb)

# ---------- СТАТИСТИКА ----------
@dp.message_handler(lambda m: m.text == "📊 Статистика")
async def stats(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    sql.execute("SELECT COUNT(*) FROM users")
    users = sql.fetchone()[0]

    sql.execute("SELECT COUNT(*) FROM keys WHERE used=1")
    used = sql.fetchone()[0]

    await msg.answer(
        f"📊 Статистика:\n\n👥 Пользователей: {users}\n🔑 Выдано ключей: {used}"
    )

# ---------- РАССЫЛКА ----------
broadcast = {}

@dp.message_handler(lambda m: m.text == "📨 Рассылка")
async def broadcast_start(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        broadcast[msg.from_user.id] = True
        await msg.answer("✉️ Отправьте текст")

@dp.message_handler()
async def broadcast_send(msg: types.Message):
    if broadcast.get(msg.from_user.id):
        broadcast[msg.from_user.id] = False

        sql.execute("SELECT user_id FROM users")
        users = sql.fetchall()

        for u in users:
            try:
                await bot.send_message(u[0], msg.text)
            except:
                pass

        await msg.answer("✅ Рассылка завершена")

# ================= ЗАПУСК =================
executor.start_polling(dp)
