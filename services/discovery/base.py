from typing import Any

from api.client import StratzClient
from api.queries import LEADERBOARD_HERO_QUERY, PLAYER_MATCHES_QUERY
from config import Config
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository


class BaseDiscoveryService:
    """Shared infrastructure for hero/player-based match discovery."""

    def __init__(
        self,
        client: StratzClient,
        hero_repository: HeroRepository,
        match_repository: MatchRepository,
    ) -> None:
        self.client = client
        self.hero_repository = hero_repository
        self.match_repository = match_repository

    def _fetch_top_players(self, hero_id: int, take: int) -> list[int]:
        result = self.client.execute(
            LEADERBOARD_HERO_QUERY,
            {
                "heroIds": [hero_id],
                "bracketIds": [Config.LEADERBOARD_BRACKET],
                "take": take,
            },
        )
        leaderboard = result.get("leaderboard", {}).get("hero") or []
        return [
            entry["steamAccountId"]
            for entry in leaderboard
            if entry.get("steamAccountId")
        ]

    def _fetch_player_matches(
        self, player_id: int, hero_id: int, take: int
    ) -> list[dict[str, Any]]:
        result = self.client.execute(
            PLAYER_MATCHES_QUERY,
            {
                "steamAccountId": player_id,
                "heroIds": [hero_id],
                "take": take,
            },
        )
        return result.get("player", {}).get("matches") or []
