"""Regression contract for the destructive-risk deployment path.

These tests intentionally inspect the shell entrypoint: it is the artifact that
executes on production, where replacing containers without a verified SQLite
backup can lose the only copy of the racing history.
"""

from pathlib import Path
import re


SCRIPT = Path(__file__).resolve().parents[1] / "manage_remote.sh"


def _function_body(name: str) -> str:
    source = SCRIPT.read_text()
    match = re.search(rf"^function {re.escape(name)}\(\) \{{", source, re.MULTILINE)
    assert match, f"manage_remote.sh must define function {name}()"
    next_function = re.search(r"^function \w+\(\) \{", source[match.end() :], re.MULTILINE)
    end = match.end() + next_function.start() if next_function else len(source)
    return source[match.start() : end]


def _full_update_body() -> str:
    return _function_body("full_update")


def test_full_update_is_exposed_as_a_dedicated_command():
    source = SCRIPT.read_text()

    assert re.search(r'^\s*full-update\)\s*\n\s*full_update\s*\n\s*;;', source, re.MULTILINE), (
        "A destructive complete refresh must require explicit `./manage_remote.sh full-update`, "
        "rather than silently changing the lightweight update command."
    )


def test_full_update_fast_forwards_git_before_recreating_containers():
    body = _full_update_body()

    pull_at = body.index("git pull --ff-only")
    recreate_at = body.index("up -d --build --force-recreate")
    assert pull_at < recreate_at


def test_full_update_verifies_xray_secret_before_recreating_containers():
    body = _full_update_body()

    preflight_at = body.index("secrets/xray-telegram.json")
    recreate_at = body.index("up -d --build --force-recreate")
    assert preflight_at < recreate_at


def test_full_update_makes_verified_sqlite_backup_before_recreating_containers():
    body = _full_update_body()

    backup_at = body.index(".backup(")
    assert "sqlite3.connect" in body
    assert "PRAGMA integrity_check" in body
    assert backup_at < body.index("up -d --build --force-recreate")


def test_full_update_validates_compose_and_never_tears_down_volumes():
    body = _full_update_body()

    config_at = body.index("config -q")
    recreate_at = body.index("up -d --build --force-recreate")
    assert config_at < recreate_at
    assert "down" not in body
    assert "-v" not in body
    assert "--remove-orphans" in body


def test_full_update_runs_xray_validation_with_the_image_entrypoint_once():
    body = _full_update_body()

    assert "--entrypoint xray carting-xray run -test -c /etc/xray/config.json" in body
    assert "carting-xray xray run -test" not in body


def test_full_update_accepts_a_root_owned_xray_secret_for_container_validation():
    body = _full_update_body()

    assert '[ ! -f "secrets/xray-telegram.json" ]' in body
    assert '[ ! -r "secrets/xray-telegram.json" ]' not in body


def test_full_update_checks_the_actual_api_health_route_after_recreation():
    body = _full_update_body()

    assert "http://127.0.0.1:8000/api/health" in body
