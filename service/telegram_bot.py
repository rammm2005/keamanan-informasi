import os
import time
import uuid
from datetime import datetime

from dotenv import load_dotenv
from Crypto.Random import get_random_bytes
from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad, unpad

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

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ================== 🔐 3DES Class ==================

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

# ================== 🧩 Utils ==================

def is_hex(s: str) -> bool:
    try:
        bytes.fromhex(s)
        return True
    except ValueError:
        return False

def now_time():
    return datetime.now().strftime("%H:%M:%S")

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

async def safe_edit_or_send(query, context, text, **kwargs):
    try:
        await query.edit_message_text(text=text, **kwargs)
    except telegram.error.BadRequest:
        await context.bot.send_message(chat_id=query.message.chat_id, text=text, **kwargs)

# ================== 🗝️ State ==================

user_keys: dict[int, bytes] = {}
user_crypto_mode: dict[int, str] = {}
user_crypto: dict[int, TripleDES] = {}
user_mode: dict[int, str] = {}
user_text: dict[int, str] = {}

# ================== 🚪 Handlers ==================

async def start(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    key_24 = get_random_bytes(24)
    algo_mode = 'EDE'
    crypto_mode = 'encrypt'

    user_keys[chat_id] = key_24
    user_crypto_mode[chat_id] = algo_mode
    user_crypto[chat_id] = TripleDES(key_24, algo_mode)
    user_mode[chat_id] = crypto_mode

    await update.message.reply_text(
        f"👋 *Selamat datang di Bot 3DES!*\n\n"
        f"🔑 Kunci baru dibuat & disimpan.\n"
        f"📄 Kunci hex: `{key_24.hex()}`\n"
        f"💡 Simpan kunci ini untuk dekripsi nanti.\n\n"
        f"⚙️ Algoritma: `{algo_mode}`\n"
        f"📄 Mode: `Enkripsi`\n\n"
        f"➡️ Kirim teks atau file untuk diproses.",
        reply_markup=mode_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def mode_chosen(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data in ["set_encrypt", "set_decrypt"]:
        mode = query.data.replace("set_", "")
        user_mode[chat_id] = mode
        mode_label = "Enkripsi" if mode == "encrypt" else "Dekripsi"
        await safe_edit_or_send(
            query, context,
            f"✅ Mode diubah ke: *{mode_label}*\n"
            f"⚙️ Algoritma: `{user_crypto_mode[chat_id]}`\n\n"
            f"➡️ Kirim teks atau file untuk diproses.",
            reply_markup=mode_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif query.data.startswith("set_"):
        algo_mode = query.data.replace("set_", "")
        key_24 = user_keys[chat_id]
        user_crypto_mode[chat_id] = algo_mode
        user_crypto[chat_id] = TripleDES(key_24, algo_mode)

        mode_label = user_mode.get(chat_id, "encrypt")
        mode_str = "Enkripsi" if mode_label == "encrypt" else "Dekripsi"

        await safe_edit_or_send(
            query, context,
            f"✅ Algoritma diubah ke: `{algo_mode}`\n"
            f"📄 Mode saat ini: *{mode_str}*\n\n"
            f"➡️ Kirim teks atau file untuk diproses.",
            reply_markup=mode_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

async def text_received(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    mode = user_mode.get(chat_id)

    if not mode:
        await update.message.reply_text(
            "⚠️ Pilih mode dulu dengan /start atau tombol di bawah.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    user_text[chat_id] = text
    mode_label = "Enkripsi" if mode == "encrypt" else "Dekripsi"

    await update.message.reply_text(
        f"📄 Teks diterima:\n\n`{text}`\n\nSiap untuk *{mode_label}*?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🚀 Proses {mode_label}", callback_data="process")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

async def process(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    text = user_text.pop(chat_id, "")
    mode = user_mode.get(chat_id, "")

    if not text or not mode:
        await safe_edit_or_send(query, context, "⚠️ Tidak ada teks atau mode.")
        return

    timestamp = now_time()
    mode_label = "Enkripsi" if mode == "encrypt" else "Dekripsi"

    if mode == "encrypt":
        key_24 = get_random_bytes(24)
        user_keys[chat_id] = key_24
        user_crypto[chat_id] = TripleDES(key_24, user_crypto_mode[chat_id])
        crypto = user_crypto[chat_id]
        info_key = f"🆕 Kunci baru: `{key_24.hex()}`\n\n"
    else:
        crypto = user_crypto[chat_id]
        info_key = f"🔑 Kunci: `{user_keys[chat_id].hex()}`\n\n"

    start_time = time.perf_counter()
    try:
        if mode == "encrypt":
            result = crypto.encrypt(text)
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

        elapsed = (time.perf_counter() - start_time) * 1000

        await safe_edit_or_send(
            query, context,
            f"✅ *Hasil {mode_label}*\n\n"
            f"{info_key}"
            f"*Output*: `{result}`\n\n"
            f"⏱️ {elapsed:.1f} ms | 🕒 {timestamp}",
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

    document = update.message.document or update.message.photo[-1]
    file = await document.get_file()
    original_filename = getattr(document, "file_name", f"{uuid.uuid4().hex}.bin")
    file_path = f"temp_{chat_id}.bin"
    await file.download_to_drive(file_path)

    if mode == "encrypt":
        key_24 = get_random_bytes(24)
        user_keys[chat_id] = key_24
        user_crypto[chat_id] = TripleDES(key_24, user_crypto_mode[chat_id])
        crypto = user_crypto[chat_id]
        info_key = f"🆕 Kunci baru: `{key_24.hex()}`\n"
    else:
        crypto = user_crypto[chat_id]
        info_key = f"🔑 Kunci: `{user_keys[chat_id].hex()}`\n"

    try:
        with open(file_path, "rb") as f:
            data = f.read()

        if mode == "encrypt":
            result = crypto.encrypt_bytes(data)
            out_name = f"{original_filename}.3des"
        else:
            result = crypto.decrypt_bytes(data)
            out_name = original_filename.replace(".3des", "")

        out_path = f"output_{chat_id}.bin"
        with open(out_path, "wb") as f:
            f.write(result)

        await update.message.reply_document(
            document=open(out_path, "rb"),
            filename=out_name,
            caption=info_key,
            reply_markup=mode_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Gagal {mode}: `{str(e)}`",
            parse_mode=ParseMode.MARKDOWN
        )
    finally:
        os.remove(file_path)
        if os.path.exists(out_path):
            os.remove(out_path)

# ================== 🚀 Main ==================

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(mode_chosen, pattern="set_.*"))
    app.add_handler(CallbackQueryHandler(process, pattern="process"))
    app.add_handler(MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, text_received))
    app.add_handler(MessageHandler(tg_filters.Document.ALL | tg_filters.PHOTO, file_received))

    print("✅ Bot berjalan…")
    app.run_polling()
