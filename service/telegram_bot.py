import os
import time
from dotenv import load_dotenv

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters as tg_filters
)

from datetime import datetime
from Crypto.Random import get_random_bytes
from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad, unpad

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

print(f"BOT_TOKEN = {BOT_TOKEN!r}")

# ----------------------------- TripleDES -----------------------------

class TripleDES:
    def __init__(self, k1, k2, k3, mode='EDE'):
        self.keys = [k1, k2, k3]
        self.mode = mode  # 'EDE', 'EED', 'DEE'

    def _apply_3des(self, data: bytes, encrypt=True) -> bytes:
        rounds = []
        for i, letter in enumerate(self.mode):
            if letter == 'E':
                rounds.append( (self.keys[i], True) )
            elif letter == 'D':
                rounds.append( (self.keys[i], False) )

        result = data
        for key, is_enc in rounds:
            cipher = DES3.new(key*3, DES3.MODE_ECB)  # repeat 8-byte key to 24 bytes
            if encrypt:
                if is_enc:
                    result = cipher.encrypt(pad(result, 8))
                else:
                    result = unpad(cipher.decrypt(result), 8)
            else:
                if is_enc:
                    result = unpad(cipher.decrypt(result), 8)
                else:
                    result = cipher.encrypt(pad(result, 8))
        return result

    def encrypt(self, plaintext: str) -> str:
        iv = get_random_bytes(8)
        data = plaintext.encode()
        cipher = DES3.new(self.keys[0]+self.keys[1]+self.keys[2], DES3.MODE_CBC, iv)
        padded = pad(data, DES3.block_size)
        ct = cipher.encrypt(padded)
        return (iv + ct).hex()

    def decrypt(self, ciphertext_hex: str) -> str:
        data = bytes.fromhex(ciphertext_hex)
        iv, ct = data[:8], data[8:]
        cipher = DES3.new(self.keys[0]+self.keys[1]+self.keys[2], DES3.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), DES3.block_size)
        return pt.decode()

# ----------------------------- Global State -----------------------------

key1, key2, key3 = get_random_bytes(8), get_random_bytes(8), get_random_bytes(8)

crypto_mode = 'EDE'
crypto = TripleDES(key1, key2, key3, crypto_mode)

user_mode: dict[int, str] = {}
user_text: dict[int, str] = {}
user_filename: dict[int, str] = {}

# ----------------------------- Helpers -----------------------------

def mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔒 Enkripsi", callback_data="set_encrypt"),
            InlineKeyboardButton("🔓 Dekripsi", callback_data="set_decrypt")
        ],
        [
            InlineKeyboardButton("⚙️ EED", callback_data="set_EED"),
            InlineKeyboardButton("⚙️ DEE", callback_data="set_DEE"),
            InlineKeyboardButton("⚙️ EDE", callback_data="set_EDE")
        ]
    ])

def now_time():
    return datetime.now().strftime("%H:%M:%S")

async def safe_edit_or_send(query, context, text, **kwargs):
    try:
        await query.edit_message_text(text=text, **kwargs)
    except telegram.error.BadRequest:
        await context.bot.send_message(chat_id=query.message.chat_id, text=text, **kwargs)

# ----------------------------- Handlers -----------------------------

async def start(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Selamat datang di *Bot 3DES!*\n\n"
        "Silakan pilih mode yang ingin digunakan, atau kirim langsung `/encrypt teks` atau `/decrypt ciphertext`.\n\n"
        "📄 Kamu juga bisa kirim file.\n\n"
        f"🔁 Mode kunci saat ini: `{crypto.mode}`",
        reply_markup=mode_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def mode_chosen(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data in ["set_encrypt", "set_decrypt"]:
        user_mode[chat_id] = query.data.replace("set_", "")
        mode_label = "Enkripsi" if user_mode[chat_id] == "encrypt" else "Dekripsi"
        await safe_edit_or_send(
            query, context,
            f"✅ Mode: *{mode_label}*\n\nSilakan kirim teks atau file.",
            parse_mode=ParseMode.MARKDOWN
        )
    elif query.data.startswith("set_"):
        global crypto_mode, crypto
        crypto_mode = query.data.replace("set_", "")
        crypto = TripleDES(key1, key2, key3, crypto_mode)
        await safe_edit_or_send(
            query, context,
            f"✅ Mode kunci diubah ke: `{crypto_mode}`",
            reply_markup=mode_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

async def text_received(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    mode = user_mode.get(chat_id)

    if not mode:
        await update.message.reply_text(
            "⚠️ Pilih mode dulu dengan /start atau gunakan tombol di bawah.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    user_text[chat_id] = text
    mode_label = "Enkripsi" if mode == "encrypt" else "Dekripsi"

    keyboard = [
        [InlineKeyboardButton(f"🚀 Proses {mode_label}", callback_data="process")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📄 Teks diterima:\n\n`{text}`\n\nSiap untuk diproses?",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def process(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    text = user_text.get(chat_id, "")
    mode = user_mode.get(chat_id, "")

    if not text or not mode:
        await safe_edit_or_send(query, context, "⚠️ Tidak ada teks atau mode.")
        return

    start_time = time.perf_counter()
    timestamp = now_time()
    try:
        if mode == "encrypt":
            result = crypto.encrypt(text)
        elif mode == "decrypt":
            result = crypto.decrypt(text)
        elapsed = time.perf_counter() - start_time

        await safe_edit_or_send(
            query, context,
            f"✅ *Hasil {mode}:*\n\n"
            f"`{result}`\n\n"
            f"⏱️ Waktu proses: `{elapsed:.4f} detik`\n"
            f"🕒 Waktu: `{timestamp}`\n\n"
            f"🔁 Mode kunci saat ini: `{crypto.mode}`\n"
            "Pilih mode lain jika ingin:",
            reply_markup=mode_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await safe_edit_or_send(
            query, context,
            f"⚠️ Gagal {mode}: `{str(e)}`",
            reply_markup=mode_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

async def file_received(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    mode = user_mode.get(chat_id)

    if not mode:
        await update.message.reply_text(
            "⚠️ Pilih mode dulu dengan /start.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    document = None
    if update.message.document:
        document = update.message.document
    elif update.message.photo:
        document = update.message.photo[-1]
    else:
        await update.message.reply_text(
            "⚠️ Tidak ada file ditemukan.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    file = await document.get_file()
    orig_name = getattr(document, 'file_name', f"photo_{chat_id}.jpg")

    user_filename[chat_id] = orig_name
    file_path = f"temp_{chat_id}.bin"
    await file.download_to_drive(file_path)

    with open(file_path, "rb") as f:
        data = f.read()

    result_data = b""
    start_time = time.time()

    try:
        if mode == "encrypt":
            result_data = bytes.fromhex(crypto.encrypt(data.decode(errors='ignore')))
            out_name = f"{orig_name}.3des"
        elif mode == "decrypt":
            result_data = crypto.decrypt(data.decode(errors='ignore')).encode()
            out_name = orig_name.replace(".3des", "")
        elapsed = time.time() - start_time
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Gagal {mode}: `{str(e)}`",
            reply_markup=mode_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        os.remove(file_path)
        return

    out_path = f"output_{chat_id}.bin"
    with open(out_path, "wb") as f:
        f.write(result_data)

    await update.message.reply_document(
        document=open(out_path, "rb"),
        filename=out_name,
        caption=(
            f"✅ File hasil *{mode}* selesai dalam `{elapsed:.4f} detik`\n\n"
            f"🔁 Mode kunci saat ini: `{crypto.mode}`"
        ),
        reply_markup=mode_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

    os.remove(file_path)
    os.remove(out_path)

# ----------------------------- Main -----------------------------

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(mode_chosen, pattern="set_.*"))
    app.add_handler(CallbackQueryHandler(process, pattern="process"))
    app.add_handler(MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, text_received))
    app.add_handler(MessageHandler(tg_filters.Document.ALL | tg_filters.PHOTO, file_received))

    print("✅ Bot berjalan…")
    app.run_polling()
