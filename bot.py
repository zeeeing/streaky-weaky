import os, datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from api import solved_today, get_question
from db import init_db, get_state, set_state
from db import get_players, upsert_player
from classes.player import Player
from classes.group_state import GroupState

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
NODE_ENV = os.getenv("NODE_ENV", "development")
TZ = ZoneInfo(os.getenv("TZ", "Asia/Singapore"))

# select env
if NODE_ENV == "production":
    API_BASE = os.getenv("API_BASE_PROD")
else:
    API_BASE = os.getenv("API_BASE_DEV")


# helpers
def get_group_state(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> GroupState:
    key = f"group:{chat_id}"

    # load from db if not in memory
    if key not in context.bot_data:
        group = GroupState()

        # load streak state from db
        streak, today_checked = get_state(chat_id)
        group.streak = streak
        group.today_checked = today_checked

        # load players from db
        for row in get_players(chat_id):
            group.players[int(row["tele_id"])] = Player(
                tele_id=int(row["tele_id"]), lc_user=row["lc_user"]
            )

        # cache in bot_data
        context.bot_data[key] = group

    return context.bot_data[key]


def get_difficulty_icon(difficulty: str) -> str:
    """Map difficulty string to corresponding emoji icon."""
    mapping = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}
    return mapping.get(difficulty, "❓")


def perform_streak_check(
    group: GroupState, now: datetime.datetime, today: str
) -> tuple[bool, list[str]]:
    lines = [f"Date: {now.strftime('%d-%m-%Y')} (SGT)\n"]
    all_completed = True

    for _, p in group.players.items():
        solved, titles = solved_today(p.lc_user, now)
        status_icon = "✅" if solved else "❌"
        all_completed = all_completed and solved
        detailed_titles = ", ".join(titles) if titles else ""
        lines.append(f"• {p.lc_user}: {status_icon} {detailed_titles}")

    if all_completed and group.today_checked != today:
        prev_streak = group.streak
        group.streak += 1
        group.today_checked = today
        lines.append(f"\nStreak updated: {prev_streak} → {group.streak} 🔥")
    elif group.today_checked == today:
        lines.append("\nStreak already updated for today.")
    else:
        lines.append("\nStreak not updated. Keep going! 💪")

    return all_completed, lines


# 1. start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Group usage:\n\n"
        "• Add me to a group.\n"
        "• Everyone runs /link <leetcode_username>.\n\n"
        "Team streak requires all linked users to submit an accepted submission daily.\n\n"
        "Other Commands: /status, /check_now.\n"
        "Daily tally happens at 23:59 SGT or when all members have completed the requirements for the day, whichever comes first."
    )


# 2. link command
async def link_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    args = context.args

    if not args or len(args) != 1:
        await update.message.reply_text("Usage: /link <leetcode_username>")
        return

    lc_user = args[0]
    group = get_group_state(context, chat_id)

    # persist to db and update memory
    upsert_player(chat_id, user_id, lc_user)
    group.players[user_id] = Player(tele_id=user_id, lc_user=lc_user)

    await update.message.reply_text(
        f"Linked @{update.effective_user.username or user_id} to {lc_user}.\n"
        f"When everyone has linked, run /status to check."
    )


# 3. get current status of players in streak
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    group = get_group_state(context, chat_id)

    if len(group.players) < 2:
        await update.message.reply_text(
            "Need at least two linked players. Run using /link <leetcode_username>."
        )
        return

    now = datetime.datetime.now(TZ)
    lines = [f"Date: {now.strftime('%d-%m-%Y')} (SGT)\n"]

    for _, p in group.players.items():
        if not p.lc_user:
            lines.append(f"• {p.tele_id}: not linked")
            continue

        solved, titles = solved_today(p.lc_user, now)
        status_icon = "✅" if solved else "❌"

        detailed_titles = []
        for title_slug in titles:
            question = get_question(title_slug)
            difficulty_icon = get_difficulty_icon(question.get("difficulty"))

            # create md link to the lc qn
            url = question.get("link", f"https://leetcode.com/problems/{title_slug}/")
            title = question.get("title", title_slug)
            detailed_titles.append(f"[{title}]({url}) {difficulty_icon}")
        extra = f" — {', '.join(detailed_titles)}" if detailed_titles else ""
        lines.append(f"• {p.lc_user}: {status_icon}{extra}")
    lines.append(f"\nCurrent streak: {group.streak} 🔥")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# 4. manual streak check/update
async def check_now_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    group = get_group_state(context, chat_id)

    if len(group.players) < 2:
        await update.message.reply_text("Need at least two linked players. Use /link.")
        return

    now = datetime.datetime.now(TZ)
    today = now.strftime("%d-%m-%Y")

    _, lines = perform_streak_check(group, now, today)
    set_state(chat_id, group.streak, group.today_checked)

    await update.message.reply_text("\n".join(lines))


# job queue handlers
async def check_streaks(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(TZ)
    today = now.strftime("%d-%m-%Y")

    for chat_id_str, group in context.bot_data.items():
        if not isinstance(group, GroupState):
            continue

        chat_id = int(chat_id_str.split(":")[1])

        _, lines = perform_streak_check(group, now, today)
        set_state(chat_id, group.streak, group.today_checked)

        await context.bot.send_message(chat_id=chat_id, text="\n".join(lines))


def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    job_queue = app.job_queue

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link", link_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("check_now", check_now_cmd))

    # check streak daily at EOD
    job_queue.run_daily(check_streaks, time=datetime.time(23, 59, tzinfo=TZ))
    # check daily status
    job_queue.run_daily(status_cmd, time=datetime.time(8, 0, tzinfo=TZ))

    print("Polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
