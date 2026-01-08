from dotenv import load_dotenv

load_dotenv()

import os, logging
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.helpers import escape_markdown

from classes.player import Player
from utils import send_status_message

# constants
LOGGER = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Asia/Singapore"))

# --- MOCK DATA FOR TESTING ---
# Format: { tele_id (int): Player }
PLAYERS = {}

# Add dummy player for testing
dummy_p1 = Player(12345678, "tele_username_1", "lc_username_1")
PLAYERS[12345678] = dummy_p1
# --------------------------------


# 1. start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Hi, I'm Streaky Weaky 👋\n\n"
        "- Use /link <username> to link your LeetCode account and start tracking your progress.\n"
        "- Use /status to check who solved a problem today."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# 2. link command
async def link_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get user id of the telegram user
    user_id = update.effective_user.id

    # get command arguments
    args = context.args

    # validate args
    if not args or len(args) != 1:
        await update.message.reply_text("Usage: /link <leetcode_username>")
        return

    # retrieve leetcode username
    lc_username = args[0]

    # retrieve telegram username
    tele_username = update.effective_user.username or ""

    # save data to in-memory storage
    if user_id not in PLAYERS:
        PLAYERS[user_id] = Player(user_id, tele_username, lc_username)
    else:
        # update usernames if already exist (in case they changed it)
        PLAYERS[user_id].set_tele_username(tele_username)
        PLAYERS[user_id].set_lc_username(lc_username)

    # build response message
    escaped_tele_username = escape_markdown(
        tele_username or str(user_id)
    )  # fallback to user_id if no username
    escaped_lc_username = escape_markdown(lc_username)

    await update.message.reply_text(
        f"Linked tele-handle @{escaped_tele_username} to LeetCode username: `{escaped_lc_username}`.\n\n"
        f"Run /status to check progress.",
        parse_mode="Markdown",
    )


# 3. status command
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_status_message(update, context, PLAYERS)


# 4. refresh button callback
async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Refreshing data. Please wait...")
    await send_status_message(update, context, PLAYERS, is_refresh=True)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link", link_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh_status$"))

    print("Polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
