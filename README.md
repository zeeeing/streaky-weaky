# Streaky Weaky

A Telegram bot that helps you keep your daily LeetCode practice streak alive. It tracks linked members' daily submissions, posts status updates, and automatically resets streaks if a day is missed.

## Features

- **Individual Streak Tracking**: Tracks streaks for every linked user.
- **Daily Resets**: Automatically checks streaks at the end of the day (00:00 SGT) and resets them if no submission is found.
- **Live Status**: Check who has solved a problem today with `/status` and refresh the data instantly.
- **Supabase Integration**: fast and persistent storage using Supabase (PostgreSQL).
- **Handy Links**: Provides links to solved problems and difficulty indicators.

## Tech Stack

- Python, `python-telegram-bot`
- Supabase (PostgreSQL)

## Commands

- `/start` — Quick help and usage overview.
- `/link <leetcode_username>` — Link your Telegram user to a LeetCode username.
- `/status` — Show today’s completion status for all linked members. Includes a "Refresh" button to update data.

## Quick Start

### Using the Bot

1. Start the bot: `/start`
2. Link your LeetCode account:
   ```
   /link <leetcode_username>
   ```
3. Check status:
   ```
   /status
   ```
   The bot will show who has completed a problem today and their current streak.

### Local Hosting (Developer Guide)

1. **Prerequisites**: Python 3.10+ and `pip`.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Supabase Setup**:
   - Create a Supabase project.
   - Create a `players` table with the following columns:
     - `tele_id` (int8, Primary Key)
     - `tele_username` (text)
     - `lc_username` (text)
     - `streak` (int8, default 0)
     - `last_streak_upgrade` (timestamptz, nullable)
4. **Environment Variables**:
   Create a `.env` file in the project root:

   ```env
   BOT_TOKEN=your-telegram-bot-token
   NODE_ENV=development
   TIMEZONE=Asia/Singapore

   # Supabase Credentials
   SUPABASE_URL=your-supabase-project-url
   SUPABASE_KEY=your-supabase-anon-key

   # Base URLs for LeetCode API
   API_BASE_DEV=https://your-api.dev.example.com
   API_BASE_PROD=https://your-api.prod.example.com
   ```

5. **Start the bot**:
   ```bash
   python bot.py
   ```

## How It Works

- **Persistence**: Uses Supabase to store player data and streaks.
- **Global Tracking**: Currently, the bot tracks all linked users globally. The `/status` command will show every user registered in the database.
- **Scheduling**:
  - A daily job runs at **00:00 SGT** to check for missed days.
  - If a user hasn't solved a problem by then, their streak is reset to 0.
- **Timezone**: Configurable via `TIMEZONE` (defaults to `Asia/Singapore`).

## External API

The bot fetches data from a LeetCode-compatible API:

- `GET {API_BASE}/{username}/acSubmission?limit=20`
- `GET {API_BASE}/select?titleSlug=<slug>`

## Development Tips

- **Virtualenv**:
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  ```
- **Logging**: Controlled via `logging.basicConfig` in `bot.py`.

## License

MIT
