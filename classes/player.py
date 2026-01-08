from dataclasses import dataclass


@dataclass
class Player:
    _tele_id: int
    _tele_username: str = ""
    _lc_username: str = ""
    _streak: int = 0

    def __init__(self, tele_id: int, tele_username: str, lc_username: str):
        self._tele_id = tele_id
        self._tele_username = tele_username
        self._lc_username = lc_username
        self._streak = 0

    def get_tele_id(self) -> int:
        return self._tele_id

    def get_tele_username(self) -> str:
        return self._tele_username

    def get_lc_username(self) -> str:
        return self._lc_username

    def get_streak(self) -> int:
        return self._streak

    def set_tele_username(self, username: str):
        self._tele_username = username

    def set_lc_username(self, username: str):
        self._lc_username = username

    def set_streak(self, streak: int):
        self._streak = streak

    def increment_streak(self):
        self._streak += 1

    def reset_streak(self):
        self._streak = 0
