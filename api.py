import os, datetime
from typing import Dict, List, Tuple
import requests
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
NODE_ENV = os.getenv("NODE_ENV", "development")
TZ = ZoneInfo(os.getenv("TZ", "Asia/Singapore"))

# select env
if NODE_ENV == "production":
    API_BASE = os.getenv("API_BASE_PROD")
else:
    API_BASE = os.getenv("API_BASE_DEV")


def fetch_ac_submissions(username: str, limit: int = 30) -> List[dict]:
    """Return recent accepted submissions from the alfa API."""
    url = f"{API_BASE}/{username}/acSubmission?limit={limit}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    # The API returns a list of submissions with timestamps (Unix seconds)
    return data


def fetch_calendar(username: str) -> Dict[str, int]:
    """Return submission calendar mapping 'utc_midnight_epoch' -> count."""
    url = f"{API_BASE}/{username}/calendar"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


def solved_today(username: str, now: datetime.datetime) -> Tuple[bool, List[str]]:
    """Check if user has at least one AC in the SGT day window."""
    day_start = int(
        datetime.datetime(now.year, now.month, now.day, tzinfo=TZ).timestamp()
    )
    day_end = int(
        datetime.datetime(
            now.year, now.month, now.day, 23, 59, 59, tzinfo=TZ
        ).timestamp()
    )

    titles = []
    try:
        subs = fetch_ac_submissions(username, limit=30)
        for s in subs or []:
            ts = int(s.get("timestamp", 0))
            if day_start <= ts <= day_end:
                t = s.get("title") or s.get("titleSlug") or "unknown"
                titles.append(t)
        if titles:
            return True, titles
    except Exception:
        # fall through to calendar check
        pass

    # Calendar fallback
    try:
        cal = fetch_calendar(username) or {}
        # calendar keys are UTC midnight. Compute today's SGT midnight in UTC.
        sgt_midnight = datetime.datetime(now.year, now.month, now.day, tzinfo=TZ)
        utc_midnight = int(
            sgt_midnight.astimezone(datetime.timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .timestamp()
        )
        if str(utc_midnight) in cal and int(cal[str(utc_midnight)]) > 0:
            return True, ["via calendar"]
    except Exception:
        pass

    return False, []
