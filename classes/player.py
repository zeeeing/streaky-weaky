from dataclasses import dataclass


@dataclass
class Player:
    tele_id: int
    lc_user: str = ""
