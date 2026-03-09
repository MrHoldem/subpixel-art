#!/usr/bin/env python3
import os
import json
from pathlib import Path
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

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
        grayscale=u.get("mode", "dither") == "grayscale",
        dither=u.get("dither", True),
        keep_aspect=True,
    )


def set_user_opts(user_id: int, **kwargs):
    u = state.get(str(user_id), {})
    u.update(kwargs)
    state[str(user_id)] = u
    save_state(state)


def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Режим: dither", callback_data="mode:dither"),
         InlineKeyboardButton("Режим: grayscale", callback_data="mode:grayscale")],
        [InlineKeyboardButton("Ширина 600", callback_data="width:600"),
         InlineKeyboardButton("Ширина 800", callback_data="width:800"),
         InlineKeyboardButton("Ширина 1200", callback_data="width:1200")],
        [InlineKeyboardButton("Сброс", callback_data="reset"),
         InlineKeyboardButton("Статус", callback_data="status")],
        [InlineKeyboardButton("Помощь", callback_data="help")],
    ])


def help_text():
    return (
        "Команды:\n"
        "/setwidth 800 — задать ширину\n"
        "/mode grayscale|dither — режим\n"
        "/status — текущие настройки\n"
        "/reset — сброс\n"
        "\nТакже можно пользоваться кнопками ниже."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Пришли картинку — сделаю субпиксельный арт.\n"
        "По умолчанию режим: dither (без серых полутонов).",
        reply_markup=main_keyboard(),
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
        f"Текущие настройки: width={u.get('width')}, mode={u.get('mode','dither')}, dither={u.get('dither', True)}",
        reply_markup=main_keyboard(),
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.pop(str(update.effective_user.id), None)
    save_state(state)
    await update.message.reply_text("Настройки сброшены", reply_markup=main_keyboard())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(help_text(), reply_markup=main_keyboard())


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    uid = query.from_user.id
    if data.startswith("mode:"):
        mode = data.split(":", 1)[1]
        set_user_opts(uid, mode=mode, dither=(mode == "dither"))
        await query.edit_message_text(f"Режим: {mode}", reply_markup=main_keyboard())
        return
    if data.startswith("width:"):
        w = int(data.split(":", 1)[1])
        set_user_opts(uid, width=w)
        await query.edit_message_text(f"Ширина: {w}", reply_markup=main_keyboard())
        return
    if data == "status":
        u = state.get(str(uid), {})
        await query.edit_message_text(
            f"Текущие настройки: width={u.get('width')}, mode={u.get('mode','dither')}, dither={u.get('dither', True)}",
            reply_markup=main_keyboard(),
        )
        return
    if data == "reset":
        state.pop(str(uid), None)
        save_state(state)
        await query.edit_message_text("Настройки сброшены", reply_markup=main_keyboard())
        return
    if data == "help":
        await query.edit_message_text(help_text(), reply_markup=main_keyboard())
        return


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.photo[-1].get_file()
    in_path = DATA_DIR / f"in_{update.effective_user.id}_{file.file_unique_id}.png"
    out_path = DATA_DIR / f"out_{update.effective_user.id}_{file.file_unique_id}.png"

    await file.download_to_drive(str(in_path))

    options = get_user_opts(update.effective_user.id)
    make_subpixel_art(str(in_path), str(out_path), options)

    await update.message.reply_document(document=str(out_path), caption="Готово", reply_markup=main_keyboard())


async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.mime_type or not doc.mime_type.startswith("image/"):
        return await update.message.reply_text("Пришли изображение", reply_markup=main_keyboard())
    file = await doc.get_file()
    in_path = DATA_DIR / f"in_{update.effective_user.id}_{file.file_unique_id}.png"
    out_path = DATA_DIR / f"out_{update.effective_user.id}_{file.file_unique_id}.png"

    await file.download_to_drive(str(in_path))
    options = get_user_opts(update.effective_user.id)
    make_subpixel_art(str(in_path), str(out_path), options)

    await update.message.reply_document(document=str(out_path), caption="Готово", reply_markup=main_keyboard())


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN not set")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("setwidth", setwidth))
    app.add_handler(CommandHandler("mode", setmode))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_doc))

    app.run_polling()


if __name__ == "__main__":
    main()
