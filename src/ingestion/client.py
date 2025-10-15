from __future__ import annotations

import time
from typing import Any

import httpx

from ingestion.models import League, Matchup, Roster, Transaction, User

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
        raise RuntimeError("Unreachable retry loop exhausted")

    @staticmethod
    def _should_retry(status_code: int) -> bool:
        return status_code >= 500 or status_code == 429

    def __enter__(self) -> SleeperClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
