import os, datetime
from typing import Dict
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, PicklePersistence

from api import fetch_ac_submissions, fetch_calendar, solved_today
from classes.player import Player
from classes.pair_state import PairState

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
NODE_ENV = os.getenv("NODE_ENV", "development")
TZ = ZoneInfo(os.getenv("TZ", "Asia/Singapore"))

# select env
if NODE_ENV == "production":
    API_BASE = os.getenv("API_BASE_PROD")
else:
    API_BASE = os.getenv("API_BASE_DEV")


# ---------- Bot command handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi. Add me to a group with both players.\n"
        "Each player runs /link <leetcode_username>\n"
        "Use /status any time. Streak tallies at 23:59 SGT daily."
    )


def get_pair_state(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> PairState:
    key = f"pair:{chat_id}"
    if key not in context.bot_data:
        context.bot_data[key] = PairState()
    return context.bot_data[key]


async def link_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /link <leetcode_username>")
        return

    lc = args[0]
    pair = get_pair_state(context, chat_id)
    pair.players[user_id] = Player(tg_id=user_id, lc_user=lc)
    await update.message.reply_text(
        f"Linked @{update.effective_user.username or user_id} to {lc}.\n"
        f"When both of you have linked, run /status to test."
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    pair = get_pair_state(context, chat_id)

    if len(pair.players) < 2:
        await update.message.reply_text(
            "Need two players. Each runs /link <leetcode_username>."
        )
        return

    now = datetime.datetime.now(TZ)
    lines = [f"Date: {now.strftime('%Y-%m-%d')} (SGT)"]
    all_ok = True
    for pid, p in pair.players.items():
        if not p.lc_user:
            lines.append(f"• {pid}: not linked")
            all_ok = False
            continue
        ok, titles = solved_today(p.lc_user, now)
        tick = "✅" if ok else "❌"
        extra = f" — {', '.join(titles)}" if titles else ""
        lines.append(f"• {p.lc_user}: {tick}{extra}")
        all_ok = all_ok and ok

    lines.append(f"Current streak: {pair.streak}")
    await update.message.reply_text("\n".join(lines))


async def streak_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    pair = get_pair_state(context, chat_id)
    await update.message.reply_text(f"Streak: {pair.streak}")


# The daily close-out job: at 23:59 SGT, check both players and update streak
async def close_out_day(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    pair = get_pair_state(context, chat_id)
    now = datetime.datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    if len(pair.players) < 2:
        return

    if pair.today_checked == today:
        return  # already processed

    missing = []
    details = []
    for _, p in pair.players.items():
        ok, titles = solved_today(p.lc_user, now)
        if not ok:
            missing.append(p.lc_user)
        details.append((p.lc_user, ok, titles))

    if missing:
        pair.streak = 0
        pair.today_checked = today
        msg = "Streak ended. Missed today: " + ", ".join(missing)
        # Include a small detail line
        for name, ok, titles in details:
            mark = "✅" if ok else "❌"
            msg += f"\n• {name}: {mark} {', '.join(titles) if titles else ''}"
        await context.bot.send_message(chat_id=chat_id, text=msg)
    else:
        pair.streak += 1
        pair.today_checked = today
        ok_list = ", ".join(
            f"{name} ({', '.join(titles) if titles else 'ok'})"
            for name, ok, titles in details
        )
        await context.bot.send_message(
            chat_id=chat_id, text=f"Day complete. Streak = {pair.streak}\n{ok_list}"
        )


async def enable_daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Attach a daily job to this chat at 23:59 SGT."""
    chat_id = update.effective_chat.id
    pair = get_pair_state(context, chat_id)
    if len(pair.players) < 2:
        await update.message.reply_text("Link both players first using /link.")
        return

    # Remove existing jobs for this chat
    for j in context.job_queue.get_jobs_by_name(f"closeout-{chat_id}"):
        j.schedule_removal()

    # Schedule at 23:59:00 SGT daily
    run_time = datetime.time(23, 59, 0, tzinfo=TZ)
    context.job_queue.run_daily(
        close_out_day, time=run_time, chat_id=chat_id, name=f"closeout-{chat_id}"
    )
    await update.message.reply_text(
        "Daily check scheduled at 23:59 SGT. Use /status to see live state."
    )


async def check_now_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual check now."""
    chat_id = update.effective_chat.id
    pair = get_pair_state(context, chat_id)
    if len(pair.players) < 2:
        await update.message.reply_text(
            "Need two players. Each runs /link <leetcode_username>."
        )
        return
    now = datetime.datetime.now(TZ)
    lines = []
    ok_both = True
    for _, p in pair.players.items():
        ok, titles = solved_today(p.lc_user, now)
        tick = "✅" if ok else "❌"
        ok_both = ok_both and ok
        lines.append(f"{p.lc_user}: {tick} {', '.join(titles) if titles else ''}")
    await update.message.reply_text("\n".join(lines) + f"\nBoth done: {ok_both}")


def main():
    # simple persistent storage, per chat
    persistence = PicklePersistence(filepath="streak_data.pkl")
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link", link_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("streak", streak_cmd))
    app.add_handler(CommandHandler("enable_daily", enable_daily_cmd))
    app.add_handler(CommandHandler("check_now", check_now_cmd))

    print("Polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
