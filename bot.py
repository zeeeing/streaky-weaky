import os, datetime
import logging
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from api import solved_today, get_question
from db import init_db, get_state, set_state
from db import (
    get_players,
    upsert_player,
    get_all_chat_ids,
    get_group_name,
    set_group_name,
)
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

# module logger
LOGGER = logging.getLogger(__name__)


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

        # load custom group name if any
        name = get_group_name(chat_id)
        group.name = name or ""

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
        lines.append("\nStreak already updated for today. Nice work! 🎉")
    else:
        lines.append(
            "\nNot all players have completed their daily LeetCode question. Keep going! 💪"
        )

    return all_completed, lines


def build_question_links(title_slugs: list[str]) -> list[str]:
    """
    Return markdown-formatted question links with fallbacks.
    """
    details: list[str] = []
    for title_slug in title_slugs:
        url = f"https://leetcode.com/problems/{title_slug}/"
        title = title_slug.replace("-", " ").title()
        difficulty_icon = get_difficulty_icon(None)

        try:
            question = get_question(title_slug)
        except Exception as exc:
            LOGGER.warning("Failed to fetch question %s: %s", title_slug, exc)
            question = None

        if question:
            url = question.get("link", url)
            title = question.get("questionTitle", title)
            difficulty_icon = get_difficulty_icon(question.get("difficulty"))

        details.append(f"[{title}]({url}) {difficulty_icon}")

    return details


# 1. start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Hi there! Looking to keep your LeetCode practices in rhythm? Well, you've come to the right place!\n\n"
        "Private chat usage: <i>NOT CURRENTLY SUPPORTED</i>\n\n"
        "<b>Group chat usage:</b>\n"
        "1. Add me to a group.\n"
        "2. Everyone runs <code>/link &lt;leetcode_username&gt;</code> to link their leetcode username to their telegram account.\n"
        "3. Run <code>/status</code> or <code>/check_now</code> to keep update to date with the team's progress daily!\n"
        "4. Optionally set a custom group name with <code>/set_group_name &lt;your name&gt;</code>.\n\n"
        "• To prevent a streak from dying, every linked user is required to submit at least 1 accepted submission daily.\n"
        "• Daily tally happens at 23:59 SGT or when all members have completed the requirements for the day, whichever comes first."
    )
    await update.message.reply_text(text, parse_mode="HTML")


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

        solved, title_slugs = solved_today(p.lc_user, now)
        status_icon = "✅" if solved else "❌"

        detailed_titles = build_question_links(title_slugs)
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


# 5. leaderboard command
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    groups: list[tuple[str, int, int]] = []  # (display_name, streak, members)
    for cid in get_all_chat_ids():
        group = get_group_state(context, cid)

        if len(group.players) < 2:
            continue

        streak, _ = get_state(cid)
        display_name = (
            group.name.strip()
            if getattr(group, "name", "")
            else f"{update.effective_chat.title}"
        )
        groups.append((display_name, streak, len(group.players)))

    # Sort groups by streak desc, then name asc for stability
    groups.sort(key=lambda x: (-x[1], x[0].lower()))

    if not groups:
        await update.message.reply_text(
            "No eligible groups yet. Link at least two players to appear."
        )
        return

    lines = ["🏆 Group Leaderboard 🏆\n"]
    for rank, (name, streak, members) in enumerate(groups, start=1):
        lines.append(f"{rank}. {name}: {streak} 🔥 ({members} members)")

    await update.message.reply_text("\n".join(lines))


# 6. set custom group name for leaderboard
async def set_group_name_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = chat.id

    # Only sensible in group chats
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("This command can only be used in group chats.")
        return

    # Require a non-empty name
    if not context.args:
        await update.message.reply_text("Usage: /setgroupname <custom group name>")
        return

    name = " ".join(context.args).strip()
    if not name:
        await update.message.reply_text("Group name cannot be empty.")
        return

    # persist and update cache
    set_group_name(chat_id, name)
    group = get_group_state(context, chat_id)
    group.name = name

    await update.message.reply_text(f"Group name set to: {name}")


# job queue handlers
async def daily_status_update(context: ContextTypes.DEFAULT_TYPE):
    """
    Send daily status update to all groups.
    """
    for chat_id in get_all_chat_ids():
        group = get_group_state(context, chat_id)

        if len(group.players) < 2:
            continue

        now = datetime.datetime.now(TZ)
        lines = [f"Date: {now.strftime('%d-%m-%Y')} (SGT)\n"]

        for _, p in group.players.items():
            if not p.lc_user:
                lines.append(f"• {p.tele_id}: not linked")
                continue

            solved, title_slugs = solved_today(p.lc_user, now)
            status_icon = "✅" if solved else "❌"

            detailed_titles = build_question_links(title_slugs)
            extra = f" — {', '.join(detailed_titles)}" if detailed_titles else ""
            lines.append(f"• {p.lc_user}: {status_icon}{extra}")
        lines.append(f"\nCurrent streak: {group.streak} 🔥")

        await context.bot.send_message(
            chat_id=chat_id, text="\n".join(lines), parse_mode="Markdown"
        )


async def check_streaks(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(TZ)
    today = now.strftime("%d-%m-%Y")

    for chat_id in get_all_chat_ids():
        group = get_group_state(context, chat_id)

        if len(group.players) < 2:
            continue

        all_completed, lines = perform_streak_check(group, now, today)

        # break streak
        if not all_completed:
            lines.append(
                "\nNot all players have completed today's challenge. The streak has been resetted to 0. Try again tomorrow! 😔"
            )
            group.streak = 0

        set_state(chat_id, group.streak, group.today_checked)

        await context.bot.send_message(chat_id=chat_id, text="\n".join(lines))


def main():
    # Configure basic logging once at startup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    job_queue = app.job_queue

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link", link_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("check_now", check_now_cmd))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("set_group_name", set_group_name_cmd))

    # check streak daily at EOD
    job_queue.run_daily(check_streaks, time=datetime.time(23, 59, tzinfo=TZ))
    # check daily status
    job_queue.run_daily(daily_status_update, time=datetime.time(8, 0, tzinfo=TZ))

    print("Polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
