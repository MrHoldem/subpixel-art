#!/usr/bin/env python3
import os
import json
from pathlib import Path
from typing import Dict

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

from subpixel_art import make_subpixel_art
from subpixel_art.converter import SubpixelOptions

DATA_DIR = Path(os.getenv("DATA_DIR", "/home/holdem/.openclaw/workspace/subpixel-art/bot_data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "state.json"


def load_state() -> Dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: Dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


state = load_state()


def get_user_opts(user_id: int) -> SubpixelOptions:
    u = state.get(str(user_id), {})
    return SubpixelOptions(
        final_width=u.get("width"),
        grayscale=u.get("mode", "grayscale") == "grayscale",
        dither=u.get("dither", False),
        keep_aspect=True,
    )


def set_user_opts(user_id: int, **kwargs):
    u = state.get(str(user_id), {})
    u.update(kwargs)
    state[str(user_id)] = u
    save_state(state)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Пришли картинку — сделаю субпиксельный арт.\n"
        "Команды: /setwidth 800, /mode grayscale|dither, /status, /reset"
    )


async def setwidth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Использование: /setwidth 800")
    try:
        w = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("Ширина должна быть числом")
    set_user_opts(update.effective_user.id, width=w)
    await update.message.reply_text(f"Ширина установлена: {w}")


async def setmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Использование: /mode grayscale|dither")
    mode = context.args[0].lower()
    if mode not in ("grayscale", "dither"):
        return await update.message.reply_text("Доступно: grayscale, dither")
    set_user_opts(update.effective_user.id, mode=mode, dither=(mode == "dither"))
    await update.message.reply_text(f"Режим: {mode}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = state.get(str(update.effective_user.id), {})
    await update.message.reply_text(
        f"Текущие настройки: width={u.get('width')}, mode={u.get('mode','grayscale')}, dither={u.get('dither', False)}"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.pop(str(update.effective_user.id), None)
    save_state(state)
    await update.message.reply_text("Настройки сброшены")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.photo[-1].get_file()
    in_path = DATA_DIR / f"in_{update.effective_user.id}_{file.file_unique_id}.png"
    out_path = DATA_DIR / f"out_{update.effective_user.id}_{file.file_unique_id}.png"

    await file.download_to_drive(str(in_path))

    options = get_user_opts(update.effective_user.id)
    make_subpixel_art(str(in_path), str(out_path), options)

    await update.message.reply_document(document=str(out_path), caption="Готово")


async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.mime_type or not doc.mime_type.startswith("image/"):
        return await update.message.reply_text("Пришли изображение")
    file = await doc.get_file()
    in_path = DATA_DIR / f"in_{update.effective_user.id}_{file.file_unique_id}.png"
    out_path = DATA_DIR / f"out_{update.effective_user.id}_{file.file_unique_id}.png"

    await file.download_to_drive(str(in_path))
    options = get_user_opts(update.effective_user.id)
    make_subpixel_art(str(in_path), str(out_path), options)

    await update.message.reply_document(document=str(out_path), caption="Готово")


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN not set")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setwidth", setwidth))
    app.add_handler(CommandHandler("mode", setmode))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_doc))

    app.run_polling()


if __name__ == "__main__":
    main()
