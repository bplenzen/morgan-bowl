from __future__ import annotations

import time
from typing import Any

import httpx

from ingestion.models import DraftPick, League, Matchup, Roster, Transaction, User

DEFAULT_BASE_URL = "https://api.sleeper.app/v1"
DEFAULT_TIMEOUT = 10.0


class SleeperClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url, timeout=timeout, transport=transport
        )
        self._max_retries = max_retries

    def close(self) -> None:
        self._client.close()

    def get_league(self, league_id: str) -> League:
        payload = self._get(f"/league/{league_id}")
        return League.model_validate(payload)

    def get_matchups(self, league_id: str, *, week: int) -> list[Matchup]:
        payload = self._get(f"/league/{league_id}/matchups/{week}")
        return [Matchup.model_validate(item) for item in payload]

    def get_users(self, league_id: str) -> list[User]:
        payload = self._get(f"/league/{league_id}/users")
        return [User.model_validate(item) for item in payload]

    def get_rosters(self, league_id: str) -> list[Roster]:
        payload = self._get(f"/league/{league_id}/rosters")
        return [Roster.model_validate(item) for item in payload]

    def get_transactions(self, league_id: str, *, week: int) -> list[Transaction]:
        payload = self._get(f"/league/{league_id}/transactions/{week}")
        return [Transaction.model_validate(item) for item in payload]

    def get_drafts(self, league_id: str) -> list[dict[str, Any]]:
        """Get all drafts for a league.

        Returns list of draft metadata. Use draft_id to fetch picks.
        """
        return self._get(f"/league/{league_id}/drafts")

    def get_draft_picks(self, draft_id: str) -> list[DraftPick]:
        """Get all picks for a specific draft.

        Args:
            draft_id: The draft identifier from get_drafts()

        Returns:
            List of DraftPick objects
        """
        payload = self._get(f"/draft/{draft_id}/picks")
        return [DraftPick.model_validate(item) for item in payload]

    def get_player_stats(self, season: int, week: int) -> dict[str, dict[str, Any]]:
        """Get player stats for a specific week.

        Args:
            season: Season year (e.g., 2025)
            week: Week number (1-18)

        Returns:
            Dict mapping player_id to stats dict with pts_ppr, gp, etc.
        """
        return self._get(f"/stats/nfl/regular/{season}/{week}")

    def _get(self, url: str) -> Any:
        return self._request("GET", url)

    def _request(self, method: str, url: str) -> Any:
        delay = 0.5
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.request(method, url)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if (
                    not self._should_retry(exc.response.status_code)
                    or attempt == self._max_retries
                ):
                    raise
                time.sleep(delay)
                delay *= 2
            except httpx.HTTPError:
                if attempt == self._max_retries:
                    raise
                time.sleep(delay)
                delay *= 2
        # Defensive: Should never reach here due to raises above, but included for type safety
        # and as a safety net if retry logic is modified
        raise RuntimeError("Retry loop exhausted unexpectedly")

    @staticmethod
    def _should_retry(status_code: int) -> bool:
        return status_code >= 500 or status_code == 429

    def __enter__(self) -> SleeperClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
