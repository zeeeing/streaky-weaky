import os
import logging
from typing import Optional, Dict
from datetime import datetime
from supabase import create_client, Client
from classes.player import Player

LOGGER = logging.getLogger(__name__)

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

if not url or not key:
    LOGGER.warning("SUPABASE_URL or SUPABASE_KEY not found in environment variables.")
    supabase: Optional[Client] = None
else:
    supabase: Client = create_client(url, key)


# helper to parse ISO timestamp strings to datetime objects
def _parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str)
    except ValueError:
        # Handle 'Z' if python < 3.11
        if ts_str.endswith("Z"):
            return datetime.fromisoformat(ts_str[:-1] + "+00:00")
        return None


def add_player(tele_id: int, tele_username: str, lc_username: str) -> bool:
    """Adds a new player to the database."""
    if not supabase:
        return False
    try:
        data = {
            "tele_id": tele_id,
            "tele_username": tele_username,
            "lc_username": lc_username,
            "streak": 0,
            "last_streak_upgrade": None,
        }
        supabase.table("players").insert(data).execute()
        return True
    except Exception as e:
        LOGGER.error(f"Error adding player {tele_id}: {e}")
        return False


def get_player(tele_id: int) -> Optional[Player]:
    """Retrieves a player by their Telegram ID."""
    if not supabase:
        return None
    try:
        response = (
            supabase.table("players").select("*").eq("tele_id", tele_id).execute()
        )
        if response.data:
            p_data = response.data[0]
            last_upgrade = _parse_timestamp(p_data.get("last_streak_upgrade"))
            player = Player(
                p_data["tele_id"],
                p_data["tele_username"],
                p_data["lc_username"],
                last_upgrade,
            )
            player.set_streak(p_data.get("streak", 0))
            return player
        return None
    except Exception as e:
        LOGGER.error(f"Error getting player {tele_id}: {e}")
        return None


def get_all_players() -> Dict[int, Player]:
    """Retrieves all players and returns them as a dictionary keyed by tele_id."""
    players = {}
    if not supabase:
        return players
    try:
        response = supabase.table("players").select("*").execute()
        for p_data in response.data:
            last_upgrade = _parse_timestamp(p_data.get("last_streak_upgrade"))
            player = Player(
                p_data["tele_id"],
                p_data["tele_username"],
                p_data["lc_username"],
                last_upgrade,
            )
            player.set_streak(p_data.get("streak", 0))
            players[p_data["tele_id"]] = player
    except Exception as e:
        LOGGER.error(f"Error getting all players: {e}")

    return players


def update_player_lc_username(tele_id: int, lc_username: str) -> bool:
    """Updates a player's LeetCode username."""
    if not supabase:
        return False
    try:
        supabase.table("players").update({"lc_username": lc_username}).eq(
            "tele_id", tele_id
        ).execute()
        return True
    except Exception as e:
        LOGGER.error(f"Error updating lc_username for {tele_id}: {e}")
        return False


def update_player_tele_username(tele_id: int, tele_username: str) -> bool:
    """Updates a player's Telegram username."""
    if not supabase:
        return False
    try:
        supabase.table("players").update({"tele_username": tele_username}).eq(
            "tele_id", tele_id
        ).execute()
        return True
    except Exception as e:
        LOGGER.error(f"Error updating tele_username for {tele_id}: {e}")
        return False


def update_streak(tele_id: int, streak: int, last_streak_upgrade: datetime) -> bool:
    """Updates a player's current streak and the last upgrade timestamp."""
    if not supabase:
        return False
    try:
        data = {
            "streak": streak,
            "last_streak_upgrade": last_streak_upgrade.isoformat(),
        }
        supabase.table("players").update(data).eq("tele_id", tele_id).execute()
        return True
    except Exception as e:
        LOGGER.error(f"Error updating streak for {tele_id}: {e}")
        return False


def reset_streak(tele_id: int) -> bool:
    """Resets a player's streak to 0."""
    if not supabase:
        return False
    try:
        supabase.table("players").update({"streak": 0}).eq("tele_id", tele_id).execute()
        return True
    except Exception as e:
        LOGGER.error(f"Error resetting streak for {tele_id}: {e}")
        return False
