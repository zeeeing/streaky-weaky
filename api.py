import os, datetime
from typing import Dict, List, Tuple, TypedDict
import requests
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
NODE_ENV = os.getenv("NODE_ENV", "development")
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Asia/Singapore"))

# select env
if NODE_ENV == "production":
    API_BASE = os.getenv("API_BASE_PROD")
else:
    API_BASE = os.getenv("API_BASE_DEV")


class ACSubmissionsResponse(TypedDict):
    """Returns a specified number of the user's last accepted submission.

    JSON object with fields:
    - count: integer count of submissions returned
    - submission: list of JSON objects with string-valued fields
    """

    count: int
    submission: List[Dict[str, str]]


def fetch_ac_submissions(username: str, limit: int = 20) -> ACSubmissionsResponse:
    """Return a JSON object with `count` and `submission` fields.
    `submission` is a list of JSON objects whose fields are strings.
    Default limit set to 20.
    """
    url = f"{API_BASE}/{username}/acSubmission?limit={limit}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


def solved_today(username: str, now: datetime.datetime) -> Tuple[bool, List[str]]:
    """Check if user has at least one AC in the SGT day window."""
    day_start = int(
        datetime.datetime(now.year, now.month, now.day, tzinfo=TIMEZONE).timestamp()
    )
    day_end = int(
        datetime.datetime(
            now.year, now.month, now.day, 23, 59, 59, tzinfo=TIMEZONE
        ).timestamp()
    )

    titles = []
    try:
        resp = fetch_ac_submissions(username)
        subs = resp.get("submission", [])
        for s in subs:
            ts = int(s.get("timestamp", 0))
            if day_start <= ts <= day_end:
                t = s.get("titleSlug")
                titles.append(t)
        if titles:
            return True, titles
    except Exception:
        # fall through to calendar check
        pass

    return False, []


def get_question(title_slug: str) -> dict:
    """
    Fetch the full question object from the API.

    Args:
        title_slug (str): The title slug of the question.

    Returns:
        dict: The full question object containing details like difficulty, title, etc.
    """
    api_url = f"{API_BASE}/select?titleSlug={title_slug}"
    response = requests.get(api_url)
    response.raise_for_status()  # Raise an error for bad HTTP responses

    return response.json()
