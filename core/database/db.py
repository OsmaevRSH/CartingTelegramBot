import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

try:
    from core.config.config import (
        DATABASE_PATH,
        PAIRING_CODE_TTL_SECONDS,
        REFRESH_TOKEN_TTL_SECONDS,
    )
    DB_FILE = Path(DATABASE_PATH)
except ImportError:
    DB_FILE = Path(__file__).parent.parent.parent / "data" / "races.db"
    PAIRING_CODE_TTL_SECONDS = 600
    REFRESH_TOKEN_TTL_SECONDS = 2_592_000


def _get_conn():
    """Получает соединение с базой данных."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DB_FILE.exists():
        DB_FILE.touch(mode=0o666)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def clear_db():
    """Полностью очищает базу данных."""
    with _get_conn() as conn:
        conn.execute("DROP TABLE IF EXISTS user_competitors")
        conn.commit()


def init_db():
    """Ensure SQLite schema exists and apply migrations."""
    print(f"🗃️  Инициализация базы данных: {DB_FILE}")

    try:
        import os
        if DB_FILE.exists():
            os.chmod(DB_FILE, 0o666)
    except Exception:
        pass

    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_competitors (
                user_id INTEGER,
                date TEXT,
                race_number TEXT,
                race_href TEXT,
                competitor_id TEXT,
                num TEXT,
                name TEXT,
                pos INTEGER,
                laps INTEGER,
                theor_lap INTEGER,
                best_lap TEXT,
                binary_laps TEXT,
                theor_lap_formatted TEXT,
                display_name TEXT,
                gap_to_leader TEXT,
                lap_times_json TEXT,
                best_lap_ms INTEGER,
                PRIMARY KEY (user_id, date, race_number, num)
            )
            """
        )
        conn.commit()

        try:
            conn.execute("ALTER TABLE user_competitors ADD COLUMN best_lap_ms INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        rows = conn.execute(
            "SELECT rowid, best_lap FROM user_competitors WHERE best_lap_ms IS NULL AND best_lap IS NOT NULL AND best_lap != ''"
        ).fetchall()
        if rows:
            for rowid, best_lap in rows:
                ms = _time_string_to_ms(best_lap)
                if ms < 999999999:
                    conn.execute(
                        "UPDATE user_competitors SET best_lap_ms = ? WHERE rowid = ?",
                        (ms, rowid),
                    )
            conn.commit()
            print(f"✅ Мигрировано {len(rows)} записей best_lap_ms")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                telegram_name TEXT,
                telegram_username TEXT,
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()

        try:
            conn.execute("ALTER TABLE user_profiles ADD COLUMN telegram_username TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE user_profiles ADD COLUMN photo_url TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mobile_pairing_codes (
                code_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                consumed_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mobile_refresh_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT
            )
            """
        )
        conn.commit()

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_competitors'"
        )
        if cursor.fetchone():
            print("✅ База данных успешно инициализирована")
        else:
            print("❌ Ошибка создания базы данных")
            raise RuntimeError("Failed to create database table")


def create_pairing_code(user_id: int) -> str:
    """Create a short-lived one-time mobile pairing code for a Telegram user."""
    code = secrets.token_urlsafe(24)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=PAIRING_CODE_TTL_SECONDS)
    ).isoformat()
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO mobile_pairing_codes (code_hash, user_id, expires_at, consumed_at)
            VALUES (?, ?, ?, NULL)
            """,
            (_token_hash(code), user_id, expires_at),
        )
    return code


def consume_pairing_code(code: str) -> Optional[int]:
    """Consume a valid pairing code once and return its user ID."""
    now = _utc_now_iso()
    with _get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT user_id FROM mobile_pairing_codes
            WHERE code_hash = ? AND consumed_at IS NULL AND expires_at > ?
            """,
            (_token_hash(code), now),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE mobile_pairing_codes
            SET consumed_at = ?
            WHERE code_hash = ? AND consumed_at IS NULL
            """,
            (now, _token_hash(code)),
        )
        return row[0]


def create_refresh_session(user_id: int) -> str:
    """Create a refresh session and return its opaque token."""
    token = secrets.token_urlsafe(48)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS)
    ).isoformat()
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO mobile_refresh_sessions (token_hash, user_id, expires_at, revoked_at)
            VALUES (?, ?, ?, NULL)
            """,
            (_token_hash(token), user_id, expires_at),
        )
    return token


def rotate_refresh_session(token: str) -> Optional[tuple[int, str]]:
    """Revoke a valid refresh token and return its user ID with a replacement token."""
    now = _utc_now_iso()
    token_hash = _token_hash(token)
    replacement = secrets.token_urlsafe(48)
    replacement_expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS)
    ).isoformat()
    with _get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT user_id FROM mobile_refresh_sessions
            WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?
            """,
            (token_hash, now),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE mobile_refresh_sessions
            SET revoked_at = ?
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (now, token_hash),
        )
        conn.execute(
            """
            INSERT INTO mobile_refresh_sessions (token_hash, user_id, expires_at, revoked_at)
            VALUES (?, ?, ?, NULL)
            """,
            (_token_hash(replacement), row[0], replacement_expires_at),
        )
    return row[0], replacement


def revoke_refresh_session(token: str) -> bool:
    """Revoke an active refresh session, returning whether it was active."""
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE mobile_refresh_sessions
            SET revoked_at = ?
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (_utc_now_iso(), _token_hash(token)),
        )
    return cursor.rowcount == 1


def save_competitor(
    user_id: int, date: str, race_number: str, race_href: str, competitor_data: Dict[str, Any]
) -> bool:
    """Insert competitor data for user; return True if inserted, False if duplicate."""
    try:
        lap_times_json = json.dumps([
            {
                'lap_number': lap.lap_number,
                'lap_time': lap.lap_time,
                'sector1': lap.sector1,
                'sector2': lap.sector2,
                'sector3': lap.sector3,
                'sector4': lap.sector4,
            }
            for lap in competitor_data.get('lap_times', [])
        ]) if competitor_data.get('lap_times') else None

        best_lap_ms = _time_string_to_ms(competitor_data['best_lap'])
        if best_lap_ms >= 999999999:
            best_lap_ms = None

        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO user_competitors (
                    user_id, date, race_number, race_href, competitor_id, num, name, pos, laps,
                    theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name,
                    gap_to_leader, lap_times_json, best_lap_ms
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    user_id,
                    date,
                    race_number,
                    race_href,
                    competitor_data['id'],
                    competitor_data['num'],
                    competitor_data['name'],
                    competitor_data['pos'],
                    competitor_data['laps'],
                    competitor_data['theor_lap'],
                    competitor_data['best_lap'],
                    competitor_data['binary_laps'],
                    competitor_data['theor_lap_formatted'],
                    competitor_data['display_name'],
                    competitor_data['gap_to_leader'],
                    lap_times_json,
                    best_lap_ms,
                ),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def get_user_competitors(user_id: int):
    """Return list of competitor data sorted by date desc."""
    with _get_conn() as conn:
        cur = conn.execute(
            """
            SELECT date, race_number, race_href, competitor_id, num, name, pos, laps,
                   theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name,
                   gap_to_leader, lap_times_json
            FROM user_competitors
            WHERE user_id=?
            ORDER BY substr(date,7,4) || substr(date,4,2) || substr(date,1,2) DESC
            """,
            (user_id,),
        )
        return cur.fetchall()


def get_competitor_by_key(user_id: int, date: str, race_number: str, num: str):
    """Get specific competitor data by key."""
    with _get_conn() as conn:
        cur = conn.execute(
            """
            SELECT date, race_number, race_href, competitor_id, num, name, pos, laps,
                   theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name,
                   gap_to_leader, lap_times_json
            FROM user_competitors
            WHERE user_id=? AND date=? AND race_number=? AND num=?
            """,
            (user_id, date, race_number, num),
        )
        return cur.fetchone()


def delete_competitor(user_id: int, date: str, race_number: str, num: str):
    """Delete competitor; return True if row deleted."""
    with _get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM user_competitors WHERE user_id=? AND date=? AND race_number=? AND num=?",
            (user_id, date, race_number, num),
        )
        conn.commit()
        return cur.rowcount > 0


def get_all_competitors():
    """Get all competitors from all users."""
    with _get_conn() as conn:
        cur = conn.execute(
            """
            SELECT user_id, date, race_number, race_href, competitor_id, num, name, pos, laps,
                   theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name,
                   gap_to_leader, lap_times_json
            FROM user_competitors
            ORDER BY substr(date,7,4) || substr(date,4,2) || substr(date,1,2) DESC
            """,
        )
        return cur.fetchall()


def upsert_user_profile(user_id: int, telegram_name: str, telegram_username: str = None, photo_url: str = None):
    """Сохраняет или обновляет Telegram-имя, username и аватар пользователя."""
    if not telegram_name or not telegram_name.strip():
        return
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO user_profiles (user_id, telegram_name, telegram_username, photo_url, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                telegram_name = excluded.telegram_name,
                telegram_username = COALESCE(excluded.telegram_username, telegram_username),
                photo_url = COALESCE(excluded.photo_url, photo_url),
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                telegram_name.strip(),
                telegram_username.strip() if telegram_username else None,
                photo_url if photo_url else None,
            ),
        )
        conn.commit()


def get_all_users():
    """Return list of {user_id, display_name, telegram_username} for all users with saved races."""
    with _get_conn() as conn:
        cur = conn.execute(
            """
            SELECT uc.user_id, uc.name, uc.display_name,
                   COALESCE(up.telegram_name, '') as telegram_name,
                   COALESCE(up.telegram_username, '') as telegram_username,
                   COALESCE(up.photo_url, '') as photo_url
            FROM user_competitors uc
            LEFT JOIN user_profiles up ON up.user_id = uc.user_id
            GROUP BY uc.user_id
            ORDER BY MAX(substr(uc.date,7,4) || substr(uc.date,4,2) || substr(uc.date,1,2)) DESC
            """
        )
        rows = cur.fetchall()

    result = []
    for user_id, name, display_name, telegram_name, telegram_username, photo_url in rows:
        if telegram_name and telegram_name.strip():
            label = telegram_name.strip()
        elif telegram_username and telegram_username.strip():
            label = f'@{telegram_username.strip()}'
        elif name and name.strip() and not (display_name or '').startswith('Карт #'):
            label = name.strip()
        elif display_name and display_name.strip() and not display_name.startswith('Карт #'):
            label = display_name.strip()
        else:
            label = f'ID:{user_id}'
        result.append({
            'user_id': user_id,
            'display_name': label,
            'telegram_username': telegram_username.strip() if telegram_username else None,
            'photo_url': photo_url.strip() if photo_url else None,
        })

    return result


def get_best_karts_today(today_date: str):
    """Рейтинг картов за день: лучший круг каждого карта, сортировка по возрастанию."""
    with _get_conn() as conn:
        cur = conn.execute(
            """
            WITH best_per_kart AS (
                SELECT num, MIN(best_lap_ms) AS min_ms
                FROM user_competitors
                WHERE date = ? AND best_lap_ms IS NOT NULL AND best_lap_ms > 0
                GROUP BY num
            )
            SELECT uc.num, uc.best_lap, bpk.min_ms,
                   COUNT(DISTINCT uc.user_id) AS drivers,
                   COALESCE(up.telegram_name, uc.name, '') AS best_driver,
                   COALESCE(up.photo_url, '') AS best_driver_photo
            FROM user_competitors uc
            INNER JOIN best_per_kart bpk
                ON uc.num = bpk.num AND uc.best_lap_ms = bpk.min_ms
            LEFT JOIN user_profiles up ON up.user_id = uc.user_id
            WHERE uc.date = ?
            GROUP BY uc.num
            ORDER BY bpk.min_ms ASC
            """,
            (today_date, today_date),
        )
        return cur.fetchall()


def _time_string_to_ms(time_str: str) -> int:
    """Преобразует строку времени 'M:SS.sss' в миллисекунды."""
    if not time_str or time_str == "-":
        return 999999999
    try:
        time_str = time_str.strip()
        if ':' in time_str and '.' in time_str:
            minutes, rest = time_str.split(':', 1)
            seconds, ms = rest.split('.', 1)
            return int(minutes) * 60000 + int(seconds) * 1000 + int(ms)
        return 999999999
    except Exception:
        return 999999999


def get_best_competitors(limit: int = 20):
    """Get one best-lap row per user, sorted by best_lap_ms ASC."""
    with _get_conn() as conn:
        cur = conn.execute(
            """
            WITH best_per_user AS (
                SELECT user_id, MIN(best_lap_ms) AS min_ms
                FROM user_competitors
                WHERE best_lap_ms IS NOT NULL AND best_lap_ms > 0
                GROUP BY user_id
            )
            SELECT uc.user_id, uc.date, uc.race_number, uc.num, uc.name, uc.display_name,
                   uc.theor_lap, uc.theor_lap_formatted, uc.best_lap, uc.pos,
                   COALESCE(up.telegram_name, '') as telegram_name,
                   COALESCE(up.photo_url, '') as photo_url,
                   uc.lap_times_json, uc.race_href
            FROM user_competitors uc
            INNER JOIN best_per_user bpu
                ON uc.user_id = bpu.user_id AND uc.best_lap_ms = bpu.min_ms
            LEFT JOIN user_profiles up ON up.user_id = uc.user_id
            GROUP BY uc.user_id
            ORDER BY bpu.min_ms ASC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()


def get_best_competitors_today(today_date: str, limit: int = 20):
    """Get one best-lap row per user for today, sorted by best_lap_ms ASC."""
    with _get_conn() as conn:
        cur = conn.execute(
            """
            WITH best_per_user AS (
                SELECT user_id, MIN(best_lap_ms) AS min_ms
                FROM user_competitors
                WHERE date = ? AND best_lap_ms IS NOT NULL AND best_lap_ms > 0
                GROUP BY user_id
            )
            SELECT uc.user_id, uc.date, uc.race_number, uc.num, uc.name, uc.display_name,
                   uc.theor_lap, uc.theor_lap_formatted, uc.best_lap, uc.pos,
                   COALESCE(up.telegram_name, '') as telegram_name,
                   COALESCE(up.photo_url, '') as photo_url,
                   uc.lap_times_json, uc.race_href
            FROM user_competitors uc
            INNER JOIN best_per_user bpu
                ON uc.user_id = bpu.user_id AND uc.best_lap_ms = bpu.min_ms
            LEFT JOIN user_profiles up ON up.user_id = uc.user_id
            WHERE uc.date = ?
            GROUP BY uc.user_id
            ORDER BY bpu.min_ms ASC
            LIMIT ?
            """,
            (today_date, today_date, limit),
        )
        return cur.fetchall()
