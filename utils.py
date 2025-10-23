import datetime

from telegram.ext import ContextTypes

from api import solved_today, get_question
from db import get_state, get_players, get_group_name
from classes import GroupState, Player


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

    if all_completed:
        if group.today_checked != today:
            prev_streak = group.streak
            group.streak += 1
            group.today_checked = today
            lines.append(f"\nStreak updated: {prev_streak} → {group.streak} 🔥")
        else:
            lines.append("\nStreak already updated for today. Nice work! 🎉")

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
            question = None

        if question:
            url = question.get("link", url)
            title = question.get("questionTitle", title)
            difficulty_icon = get_difficulty_icon(question.get("difficulty"))

        details.append(f"[{title}]({url}) {difficulty_icon}")

    return details
