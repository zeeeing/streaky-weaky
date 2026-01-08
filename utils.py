import os
from zoneinfo import ZoneInfo
from datetime import datetime
from typing import List, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.helpers import (
    escape_markdown,
)  # to allow special characters from being processed as markdown

from api import fetch_ac_submissions, get_question_details
from api import LeetCodeQuestion

TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Asia/Singapore"))


def solved_today(username: str, now: datetime) -> Tuple[bool, List[str]]:
    day_start = datetime(now.year, now.month, now.day, tzinfo=TIMEZONE).timestamp()
    day_end = datetime(
        now.year, now.month, now.day, 23, 59, 59, tzinfo=TIMEZONE
    ).timestamp()

    titles = []
    res = fetch_ac_submissions(username)
    if res:
        submissions = res.get("submission", [])
        for sub in submissions:
            ts = int(sub.get("timestamp", 0))
            if day_start <= ts <= day_end:
                t = sub.get("titleSlug")
                titles.append(t)
        if titles:
            return True, titles

    return False, []


def get_difficulty_icon(difficulty: str) -> str:
    mapping = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}
    return mapping.get(difficulty, "❓")


def build_question_links(title_slugs: list[str]) -> list[str]:
    links: list[str] = []
    for title_slug in title_slugs:
        url = f"https://leetcode.com/problems/{title_slug}/"
        title = title_slug.replace("-", " ").title()
        difficulty_icon = get_difficulty_icon(None)

        try:
            question: LeetCodeQuestion = get_question_details(title_slug)
        except Exception as e:
            question = None

        if question:
            url = question.get("link", url)
            title = question.get("questionTitle", title)
            difficulty_icon = get_difficulty_icon(question.get("difficulty"))

        escaped_title = escape_markdown(title)
        links.append(f"[{escaped_title}]({url}) {difficulty_icon}")

    return links


async def send_status_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE, players: dict, is_refresh=False
):
    # no players present
    if not players:
        msg = "No players linked yet. Use `/link <username>` to join!"
        if is_refresh:
            # if refreshing, edit the existing message
            await update.callback_query.edit_message_text(msg)
        else:
            # else send a new message
            await update.message.reply_text(msg)
        return

    # players present, build status message
    now = datetime.now(TIMEZONE)
    escaped_date_str = escape_markdown(now.strftime("%d/%m/%Y, %H:%M:%S"))
    lines = [f"_Last Updated: {escaped_date_str}_\n"]

    for player in players.values():
        # get lc username
        lc_username = player.get_lc_username()

        # check if solved today
        is_solved, question_slugs = solved_today(lc_username, now)

        # --- MOCK DATA FOR TESTING ---
        if lc_username == "lc_username_1":
            is_solved = True
            question_slugs = ["two-sum", "add-two-numbers"]
        # --------------------------------

        # retrieve tele username; fallback to tele id
        tele_username = player.get_tele_username()

        # build usernames
        escaped_lc_username = escape_markdown(lc_username)
        escaped_tele_username = escape_markdown(tele_username)
        status_emoji = "✅" if is_solved else "❌"
        lines.append(f"{status_emoji} @{escaped_tele_username} ({escaped_lc_username})")

        # build question links if solved
        if is_solved and question_slugs:
            links = build_question_links(question_slugs)
            for link in links:
                lines.append(f"└ {link}")
        lines.append("")

    text = "\n".join(lines)

    # add refresh button
    keyboard = [[InlineKeyboardButton("🔄 REFRESH", callback_data="refresh_status")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_refresh:
        # if refreshing, edit the existing message
        try:
            await update.callback_query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        except Exception as e:
            pass
    else:
        # send new message
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
