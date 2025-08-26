from dataclasses import dataclass, field
from typing import Dict
from .player import Player


@dataclass
class PairState:
    players: Dict[int, Player] = field(default_factory=dict)  # key: tg_id
    streak: int = 0
    last_day: str = ""  # "YYYY-MM-DD" that was last finalized
    # cache today’s check to avoid re-spam
    today_checked: str = ""  # "YYYY-MM-DD"

