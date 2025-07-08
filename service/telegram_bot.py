import os
import time
import uuid
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

class TripleDES:
    def __init__(self, key_24: bytes, mode='EDE'):
        if len(key_24) != 24:
            raise ValueError("Key harus 24 byte untuk TripleDES")
        self.key_24 = DES3.adjust_key_parity(key_24)
        self.mode = mode

    def encrypt(self, plaintext: str) -> str:
        data = pad(plaintext.encode(), 8)
        cipher = DES3.new(self.key_24, DES3.MODE_ECB)
        return cipher.encrypt(data).hex()

    def decrypt(self, ciphertext_hex: str) -> str:
        data = bytes.fromhex(ciphertext_hex)
        cipher = DES3.new(self.key_24, DES3.MODE_ECB)
        return unpad(cipher.decrypt(data), 8).decode()

    def encrypt_bytes(self, data: bytes) -> bytes:
        data = pad(data, 8)
        cipher = DES3.new(self.key_24, DES3.MODE_ECB)
        return cipher.encrypt(data)

    def decrypt_bytes(self, data: bytes) -> bytes:
        cipher = DES3.new(self.key_24, DES3.MODE_ECB)
        return unpad(cipher.decrypt(data), 8)

def is_hex(s: str) -> bool:
    try:
        bytes.fromhex(s)
        return True
    except ValueError:
        return False

user_keys: dict[int, bytes] = {}
user_crypto_mode: dict[int, str] = {}
user_crypto: dict[int, TripleDES] = {}
user_mode: dict[int, str] = {}
user_text: dict[int, str] = {}

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

async def start(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in user_keys:
        key_24 = user_keys[chat_id]
        info = "🔑 Kunci lama dipakai kembali."
    else:
        key_24 = get_random_bytes(24)
        user_keys[chat_id] = key_24
        info = "🔑 Kunci baru telah dibuat."

    mode = 'EDE'
    user_crypto_mode[chat_id] = mode
    user_crypto[chat_id] = TripleDES(key_24, mode)

    await update.message.reply_text(
        f"👋 Selamat datang di *Bot 3DES!*\n\n"
        f"{info}\n\n"
        f"📄 Kunci hex: `{key_24.hex()}`\n"
        f"💡 Simpan kunci ini untuk dekripsi nanti.\n\n"
        f"🔁 Algoritma saat ini: `{mode}`",
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
        mode = query.data.replace("set_", "")
        key_24 = user_keys[chat_id]
        user_crypto_mode[chat_id] = mode
        user_crypto[chat_id] = TripleDES(key_24, mode)
        await safe_edit_or_send(
            query, context,
            f"✅ Algoritma diubah ke: `{mode}`",
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

    await update.message.reply_text(
        f"📄 Teks diterima:\n\n`{text}`\n\nSiap untuk diproses?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🚀 Proses {mode_label}", callback_data="process")]
        ]),
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

    if mode == "encrypt":
        key_24 = get_random_bytes(24)
        user_keys[chat_id] = key_24
        user_crypto[chat_id] = TripleDES(key_24, user_crypto_mode[chat_id])
        info_key = f"🆕 Kunci baru digunakan: `{key_24.hex()}`\n\n"
    else:
        info_key = f"🔑 Kunci saat ini digunakan: `{user_keys[chat_id].hex()}`\n\n"

    crypto = user_crypto[chat_id]
    start_time = time.perf_counter()
    timestamp = now_time()
    try:
        if mode == "encrypt":
            result = crypto.encrypt(text)
            mode_label = "Enkripsi"
        elif mode == "decrypt":
            if not is_hex(text):
                await safe_edit_or_send(
                    query, context,
                    "⚠️ Teks bukan HEX valid untuk dekripsi.",
                    reply_markup=mode_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            result = crypto.decrypt(text)
            mode_label = "Dekripsi"

        elapsed = time.perf_counter() - start_time
        elapsed_ms = elapsed * 1000

        await safe_edit_or_send(
            query, context,
            f"✅ *Hasil {mode_label} (Algoritma: {user_crypto_mode[chat_id]}):*\n\n"
            f"{info_key}"
            f"*Output* `{result}`\n\n"
            f"⏱️ Waktu proses: `{elapsed:.4f} detik` (`{elapsed_ms:.1f} ms`)\n"
            f"🕒 Waktu: `{timestamp}`",
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

    user_text.pop(chat_id, None)
    user_mode.pop(chat_id, None)

async def file_received(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    mode = user_mode.get(chat_id)

    if not mode:
        await update.message.reply_text(
            "⚠️ Pilih mode dulu dengan /start.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    document = update.message.document or update.message.photo[-1]
    file = await document.get_file()
    original_filename = getattr(document, "file_name", f"{uuid.uuid4().hex}.bin")
    file_path = f"temp_{chat_id}.bin"
    await file.download_to_drive(file_path)

    if mode == "encrypt":
        key_24 = get_random_bytes(24)
        user_keys[chat_id] = key_24
        user_crypto[chat_id] = TripleDES(key_24, user_crypto_mode[chat_id])
        info_key = f"🆕 Kunci baru digunakan: `{key_24.hex()}`\n"
    else:
        info_key = f"🔑 Kunci saat ini digunakan: `{user_keys[chat_id].hex()}`\n"

    try:
        if mode == "encrypt":
            crypto = user_crypto[chat_id]
            with open(file_path, "rb") as f:
                data = f.read()
            result = crypto.encrypt_bytes(data)
            out_name = f"{original_filename}.3des"
        elif mode == "decrypt":
            crypto = user_crypto[chat_id]
            with open(file_path, "rb") as f:
                data = f.read()
            result = crypto.decrypt_bytes(data)
            out_name = original_filename.replace(".3des", "")

        out_path = f"output_{chat_id}.bin"
        with open(out_path, "wb") as f:
            f.write(result)

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Gagal {mode}: `{str(e)}`",
            reply_markup=mode_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        os.remove(file_path)
        return

    await update.message.reply_document(
        document=open(out_path, "rb"),
        filename=out_name,
        caption=info_key,
        reply_markup=mode_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

    os.remove(file_path)
    os.remove(out_path)

    user_mode.pop(chat_id, None)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(mode_chosen, pattern="set_.*"))
    app.add_handler(CallbackQueryHandler(process, pattern="process"))
    app.add_handler(MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, text_received))
    app.add_handler(MessageHandler(tg_filters.Document.ALL | tg_filters.PHOTO, file_received))

    print("✅ Bot berjalan…")
    app.run_polling()
