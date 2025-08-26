from dataclasses import dataclass


@dataclass
class Player:
    tg_id: int
    lc_user: str = ""

