import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bot.handlers.bot import ios_command
from core.auth.tokens import issue_access_token


@pytest.fixture
def access_token():
    return issue_access_token


@pytest.fixture
def competitor_payload():
    return {
        "id": "competitor-7",
        "num": "7",
        "name": "Driver",
        "pos": 1,
        "laps": 12,
        "theor_lap": 45123,
        "best_lap": "45.500",
        "binary_laps": "",
        "theor_lap_formatted": "45.123",
        "display_name": "Driver",
        "gap_to_leader": "0.000",
        "lap_times": [
            {
                "lap_number": 1,
                "lap_time": "45.500",
                "sector1": "11.000",
                "sector2": "11.100",
                "sector3": "11.200",
                "sector4": "12.200",
            }
        ],
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_mobile_stats_uses_token_subject(client, access_token):
    response = client.get(
        "/api/mobile/stats", headers=_auth(access_token(42))
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("method", ["get", "post", "delete"])
def test_mobile_stats_require_bearer_token(client, method, competitor_payload):
    request = getattr(client, method)
    path = (
        "/api/mobile/stats/10.08.2026/3/7"
        if method == "delete"
        else "/api/mobile/stats"
    )
    kwargs = {}
    if method == "post":
        kwargs["json"] = {
            "date": "10.08.2026",
            "race_number": "3",
            "race_href": "/race/3",
            "competitor": competitor_payload,
        }

    assert request(path, **kwargs).status_code == 401


def test_mobile_stats_save_and_delete_are_limited_to_token_subject(
    client, access_token, competitor_payload
):
    body = {
        "date": "10.08.2026",
        "race_number": "3",
        "race_href": "/race/3",
        "competitor": competitor_payload,
    }

    saved = client.post(
        "/api/mobile/stats", json=body, headers=_auth(access_token(42))
    )

    assert saved.status_code == 200
    assert saved.json() == {"saved": True}
    assert client.get("/api/stats/42").json()[0]["num"] == "7"
    assert client.get("/api/stats/99").json() == []
    assert client.delete(
        "/api/mobile/stats/10.08.2026/3/7",
        headers=_auth(access_token(99)),
    ).status_code == 404
    assert client.delete(
        "/api/mobile/stats/10.08.2026/3/7",
        headers=_auth(access_token(42)),
    ).json() == {"deleted": True}


def test_legacy_stats_routes_keep_accepting_explicit_user_id(
    client, competitor_payload
):
    response = client.post(
        "/api/stats",
        json={
            "user_id": 42,
            "date": "10.08.2026",
            "race_number": "3",
            "race_href": "/race/3",
            "competitor": competitor_payload,
        },
    )

    assert response.status_code == 200
    assert client.get("/api/stats/42").status_code == 200
    assert client.get("/api/stats/42").json()[0]["num"] == "7"


def test_ios_command_sends_pairing_code(monkeypatch):
    create_pairing_code = Mock(return_value="pairing-code")
    monkeypatch.setattr("bot.handlers.bot.create_pairing_code", create_pairing_code)
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(type="private"),
        effective_user=SimpleNamespace(id=42),
        effective_message=message,
    )

    asyncio.run(ios_command(update, SimpleNamespace()))

    create_pairing_code.assert_called_once_with(42)
    sent_text = message.reply_text.await_args.args[0]
    assert "Код для iOS" in sent_text
    assert "<code>pairing-code</code>" in sent_text
    assert "10 минут" in sent_text
    assert "только один раз" in sent_text
