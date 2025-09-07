#!/usr/bin/env python3
import os
import shutil
import subprocess
import uuid
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable not set")

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/models/ggml-small.bin")
# لیست نام‌های ممکن برای باینری whisper.cpp که در سیستم ممکنه باشه
BINARY_CANDIDATES = [
    "/usr/local/bin/whisper",
    "/usr/local/bin/main",
    "/usr/local/bin/whisper-cli",
    "/usr/bin/whisper",
    "whisper",
    "main",
    "whisper-cli"
]

def find_whisper_binary():
    for b in BINARY_CANDIDATES:
        path = shutil.which(b)
        if path:
            return path
    return None

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    file = None
    ext = "ogg"
    if msg.voice:
        file = await msg.voice.get_file()
        ext = "ogg"
    elif msg.audio:
        file = await msg.audio.get_file()
        ext = (msg.audio.file_name or "audio").split('.')[-1]
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("audio"):
        file = await msg.document.get_file()
        ext = (msg.document.file_name or "audio").split('.')[-1]
    else:
        await msg.reply_text("لطفاً یک پیام صوتی یا فایل صوتی بفرستید.")
        return

    tmpdir = "/tmp"
    os.makedirs(tmpdir, exist_ok=True)
    local_in = f"{tmpdir}/{uuid.uuid4()}.{ext}"
    local_wav = f"{tmpdir}/{uuid.uuid4()}.wav"

    # دانلود فایل از تلگرام
    await file.download_to_drive(local_in)

    # تبدیل به WAV 16k mono با ffmpeg
    try:
        subprocess.run(["ffmpeg", "-y", "-i", local_in, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", local_wav], check=True)
    except Exception as e:
        await msg.reply_text("خطا در تبدیل فایل صوتی (ffmpeg).")
        cleanup_files([local_in, local_wav])
        return

    whisper_bin = find_whisper_binary()
    if not whisper_bin:
        await msg.reply_text("ابزار تبدیل صدا (whisper) نصب نیست. لطفاً حساب سرور را بررسی کنید.")
        cleanup_files([local_in, local_wav])
        return

    # اجرای whisper.cpp (پارامترها ممکن است بسته به نسخهٔ CLI متفاوت باشد)
    try:
        proc = subprocess.run([whisper_bin, "-m", MODEL_PATH, "-f", local_wav], capture_output=True, text=True, timeout=300)
        out = proc.stdout.strip() or proc.stderr.strip()
    except subprocess.TimeoutExpired:
        out = "خطا: پردازش صوت طولانی شد (timeout)."
    except Exception as e:
        out = "خطا در اجرای ابزار تبدیل صدا."

    if not out:
        await msg.reply_text("متن قابل استخراج پیدا نشد یا خطا رخ داد.")
    else:
        # اگر متن خیلی طولانی است، آن را در فایل متنی بفرست
        if len(out) > 3500:
            txt_path = f"{tmpdir}/{uuid.uuid4()}.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(out)
            await msg.reply_document(open(txt_path, "rb"))
            try:
                os.remove(txt_path)
            except: pass
        else:
            await msg.reply_text(out)

    cleanup_files([local_in, local_wav])

def cleanup_files(paths):
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
        except:
            pass

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    handler = MessageHandler(filters.VOICE | filters.AUDIO | filters.Document.ALL, handle_audio)
    app.add_handler(handler)
    print("Bot started. (Polling)")
    app.run_polling()

if __name__ == "__main__":
    main()
