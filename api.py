import os, logging, requests
from typing import List, TypedDict, Optional

# constants
LOGGER = logging.getLogger(__name__)
NODE_ENV = os.getenv("NODE_ENV", "development")

if NODE_ENV == "production":
    API_BASE = os.getenv("API_BASE_PROD")
else:
    API_BASE = os.getenv("API_BASE_DEV")


# TYPE DEFINITIONS
class Submission(TypedDict):
    title: str
    titleSlug: str
    timestamp: str
    statusDisplay: str
    lang: str


class ACSubmissionResponse(TypedDict):
    count: int
    submission: List[Submission]


class TopicTag(TypedDict):
    name: str
    slug: str
    translatedName: Optional[str]


class LeetCodeQuestion(TypedDict):
    link: str
    questionId: str
    questionFrontendId: str
    questionTitle: str
    titleSlug: str
    difficulty: str
    isPaidOnly: bool
    question: str
    exampleTestcases: str
    topicTags: List[TopicTag]


# API FUNCTIONS
def fetch_ac_submissions(
    username: str, limit: int = 20
) -> Optional[ACSubmissionResponse]:
    url = f"{API_BASE}/{username}/acSubmission?limit={limit}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        LOGGER.error(f"Error fetching AC submissions for {username}: {e}")
        return None


def get_question_details(title_slug: str) -> Optional[LeetCodeQuestion]:
    api_url = f"{API_BASE}/select?titleSlug={title_slug}"
    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        LOGGER.error(f"Error fetching question {title_slug}: {e}")
        return None
