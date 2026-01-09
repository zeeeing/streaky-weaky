from dotenv import load_dotenv

load_dotenv()

import os, logging
from zoneinfo import ZoneInfo
from datetime import datetime, time, timedelta

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.helpers import escape_markdown

from utils import send_status_message
import db

# constants
LOGGER = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Asia/Singapore"))


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

    # check if player exists in DB
    existing_player = db.get_player(user_id)

    if not existing_player:
        # add new player
        success = db.add_player(user_id, tele_username, lc_username)
        if not success:
            await update.message.reply_text(
                "Error linking account. Please try again later."
            )
            return
    else:
        # update usernames if already exist
        db.update_player_tele_username(user_id, tele_username)
        db.update_player_lc_username(user_id, lc_username)

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
    players = db.get_all_players()
    await send_status_message(update, context, players)


# 4. refresh button callback
async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Refreshing data. Please wait...")
    players = db.get_all_players()
    await send_status_message(update, context, players, is_refresh=True)


# 5. daily reset job
async def daily_reset_job(context: ContextTypes.DEFAULT_TYPE):
    LOGGER.info("Running daily reset job...")
    players = db.get_all_players()
    now = datetime.now(TIMEZONE)
    yesterday_date = (now - timedelta(days=1)).date()

    for p in players.values():
        last_upgrade = p.get_last_streak_upgrade()
        reset_needed = False

        if last_upgrade:
            try:
                local_last_upgrade = last_upgrade.astimezone(TIMEZONE).date()
                # check if last upgrade date is before yesterday
                # (meaning they didn't solve any problem yesterday)
                if local_last_upgrade < yesterday_date:
                    reset_needed = True
            except Exception:
                # if timestamp parsing fails, fallback to ignore to avoid accidental resets
                pass
        else:
            # if no last upgrade recorded but streak > 0, they definitely haven't updated recently
            if p.get_streak() > 0:
                reset_needed = True

        if reset_needed and p.get_streak() > 0:
            LOGGER.info(
                f"Resetting streak for {p.get_tele_username()} (ID: {p.get_tele_id()})"
            )
            db.reset_streak(p.get_tele_id())


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

    # Schedule daily job at 00:00 SGT
    job_queue = app.job_queue
    job_queue.run_daily(daily_reset_job, time=time(0, 0, tzinfo=TIMEZONE))

    print("Polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
