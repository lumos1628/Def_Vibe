from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Hero:
    id: int
    display_name: str
    short_name: str = ""


@dataclass
class ChatWheel:
    id: int
    name: str
    label: str
    message: str
    all_chat: bool = False


@dataclass
class Match:
    match_id: int
    hero_id: int
    played_at: datetime
    steam_account_id: int
    parsed: bool = False
    has_replay_data: bool = False
    data_verified: bool = False
    unparseable: bool = False
    parse_status: str = "pending"


@dataclass
class OpenDotaMatchData:
    """Thin wrapper around the raw OpenDota match JSON."""

    raw: dict[str, Any]

    def get_players(self) -> list[dict[str, Any]]:
        return self.raw.get("players") or []

    def get_chat(self) -> list[dict[str, Any]]:
        return self.raw.get("chat") or []

    def get_start_time(self) -> int | None:
        return self.raw.get("start_time")


@dataclass
class ExportRecord:
    match_id: int
    exported_at: datetime
    output_path: str
