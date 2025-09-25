# Streaky Weaky

A Telegram bot that helps groups keep their daily LeetCode practice streak alive. It tracks whether every linked member submitted at least one accepted solution for the day, posts daily status updates, and automatically updates or resets the group streak at end-of-day (SGT).

## Features

- Group-first streak tracking with simple linking per member
- Daily reminders and end-of-day streak checks (SGT)
- Manual status and check commands
- Leaderboard across all groups using the bot
- SQLite persistence with in-memory caching for performance
- Handy problem links and difficulty icons (when API data is available)

## Tech Stack

- Python, `python-telegram-bot`
- SQLite for storage

## Commands

- `/start` — Quick help and usage overview
- `/link <leetcode_username>` — Link your Telegram user to a LeetCode username
- `/status` — Show today’s completion status for all linked members and current streak
- `/check_now` — Manually check everyone’s status and update the streak if complete
- `/leaderboard` — Show group streaks across all chats using the bot
- `/set_group_name <name>` — Set a custom name used on the leaderboard

Notes

- The bot requires at least two linked players in a chat to track a streak.
- Daily status broadcast: 08:00 SGT.
- Daily streak check/reset: 23:59 SGT.

## Quick Start

### Using the Deployed Bot (User Guide)

1. Open Telegram and search for the bot: `@StreakyWeakyBot`.
2. Tap the bot and press Start to view commands.
3. Add the bot to your group chat.
4. In the group, each member links their LeetCode account:
   - `/link <leetcode_username>`
5. Check group progress any time:
   - `/status` — shows who has completed today and the current streak
   - `/check_now` — manually re-check and update the streak if everyone is done
6. Optional: Set a custom group name for the leaderboard:
   - `/set_group_name <your group name>`
7. Daily schedule (SGT):
   - Status reminder at 08:00
   - Streak finalized at 23:59 (resets to 0 if anyone hasn’t completed)

Notes for users

- Works in group chats; private chat usage isn’t supported.
- Requires at least two linked members to track a streak.

### Local Hosting (Developer Guide)

1. Prerequisites: Python 3.10+ and `pip`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a Telegram bot via BotFather and copy the token.
4. Create a `.env` file in the project root:
   ```env
   BOT_TOKEN=123456:ABC-your-telegram-bot-token
   NODE_ENV=development
   TZ=Asia/Singapore
   # Base URLs for your LeetCode API service
   API_BASE_DEV=https://your-api.dev.example.com
   API_BASE_PROD=https://your-api.prod.example.com
   ```
5. Start the bot:
   ```bash
   python bot.py
   ```
6. In Telegram, add the bot to a group and try:
   - `/link <leetcode_username>` for each member
   - `/status` to see progress

## How It Works

- Persistence: The bot uses a local SQLite database (`streak_dev.db` in the repo root) and initializes tables on startup.
- In-memory cache: Group state is cached in `bot_data` and kept in sync with the DB.
- Scheduling: The job queue posts a daily status message (08:00 SGT) and finalizes the streak at end-of-day (23:59 SGT). If any member hasn’t solved at least one problem by then, the streak resets to 0.
- Timezone: The bot uses the `TZ` environment variable (IANA name) and defaults to `Asia/Singapore`.

## Expected External API

The bot fetches data from a LeetCode-compatible API, selected by `NODE_ENV`:

- `NODE_ENV=development` → `API_BASE_DEV`
- `NODE_ENV=production` → `API_BASE_PROD`

Endpoints used:

- `GET {API_BASE}/{username}/acSubmission?limit=20`
  - Response (example):
    ```json
    {
      "count": 5,
      "submission": [
        { "timestamp": "1727193600", "titleSlug": "two-sum" },
        { "timestamp": "1727200000", "titleSlug": "valid-anagram" }
      ]
    }
    ```
- `GET {API_BASE}/select?titleSlug=<slug>`
  - Response (example):
    ```json
    {
      "questionTitle": "Two Sum",
      "difficulty": "Easy",
      "link": "https://leetcode.com/problems/two-sum/"
    }
    ```

If the details endpoint fails, the bot falls back to a generic problem link using the slug.

## Data Model (SQLite)

- `streaks(chat_id PRIMARY KEY, streak INTEGER, today_checked TEXT)`
- `players(chat_id, tele_id, lc_user, PRIMARY KEY(chat_id, tele_id))`
- `groups(chat_id PRIMARY KEY, name TEXT)`

The database file is `streak_dev.db` by default and is created automatically.

## Development Tips

- Virtualenv (recommended):
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  ```
- Logging: set by `logging.basicConfig(level=logging.INFO)` in `bot.py`.
- Timezone: change via `TZ` (e.g., `TZ=UTC`, `TZ=America/New_York`).

## Troubleshooting

- No updates in group: Ensure the bot is added to the group and members have used `/link`.
- Streak not updating: All linked members must have at least one accepted submission within the configured SGT day window.
- Problem links show question marks: If the question details API is unavailable, the bot uses slugs and a fallback difficulty icon.

## License

Add your preferred license terms here.
