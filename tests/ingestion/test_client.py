from collections import deque

import httpx
import pytest

from ingestion.client import SleeperClient


def test_get_league_success() -> None:
    payload = {"league_id": "123", "name": "Test League"}

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))

    client = SleeperClient(transport=transport)
    league = client.get_league("123")

    assert league.id == "123"
    assert league.name == "Test League"


def test_get_matchups_success() -> None:
    payload = [
        {"matchup_id": 1, "roster_id": 10, "points": 120.5},
        {"matchup_id": 1, "roster_id": 12, "points": 110.0},
    ]

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))

    client = SleeperClient(transport=transport)
    matchups = client.get_matchups("123", week=1)

    assert len(matchups) == 2
    assert matchups[0].matchup_id == 1
    assert matchups[0].points == pytest.approx(120.5)


def test_get_users_success() -> None:
    payload = [
        {"user_id": "u1", "display_name": "Manager 1"},
        {"user_id": "u2", "display_name": "Manager 2"},
    ]

    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    client = SleeperClient(transport=transport)

    users = client.get_users("123")

    assert [user.id for user in users] == ["u1", "u2"]
    assert users[0].display_name == "Manager 1"


def test_get_rosters_success() -> None:
    payload = [
        {"roster_id": 10, "owner_id": "u1", "players": ["p1", "p2"]},
        {"roster_id": 11, "owner_id": "u2", "players": ["p3", "p4"]},
    ]

    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    client = SleeperClient(transport=transport)

    rosters = client.get_rosters("123")

    assert len(rosters) == 2
    assert rosters[0].owner_id == "u1"
    assert rosters[1].players == ["p3", "p4"]


def test_get_transactions_success() -> None:
    payload = [
        {"transaction_id": "t1", "status": "complete"},
        {"transaction_id": "t2", "status": "failed"},
    ]

    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    client = SleeperClient(transport=transport)

    transactions = client.get_transactions("123", week=1)

    assert len(transactions) == 2
    assert {tx.status for tx in transactions} == {"complete", "failed"}


def test_get_league_retries_then_succeeds() -> None:
    responses = deque(
        [
            httpx.Response(500, json={"error": "boom"}),
            httpx.Response(200, json={"league_id": "123", "name": "Retry League"}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        response = responses.popleft()
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                message="server error",
                request=request,
                response=response,
            )
        return response

    transport = httpx.MockTransport(handler)
    client = SleeperClient(transport=transport, max_retries=2)

    league = client.get_league("123")

    assert league.name == "Retry League"


def test_get_league_raises_on_client_error() -> None:
    response = httpx.Response(404, json={"error": "not found"})

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.HTTPStatusError(
            message="missing",
            request=request,
            response=response,
        )

    transport = httpx.MockTransport(handler)
    client = SleeperClient(transport=transport, max_retries=1)

    with pytest.raises(httpx.HTTPStatusError):
        client.get_league("missing")
