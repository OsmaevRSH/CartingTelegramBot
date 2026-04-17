import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

try:
    from core.config.config import DATABASE_PATH
    DB_FILE = Path(DATABASE_PATH)
except ImportError:
    DB_FILE = Path(__file__).parent.parent.parent / "data" / "races.db"


def _get_conn():
    """Получает соединение с базой данных."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DB_FILE.exists():
        DB_FILE.touch(mode=0o666)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


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

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_competitors'"
        )
        if cursor.fetchone():
            print("✅ База данных успешно инициализирована")
        else:
            print("❌ Ошибка создания базы данных")
            raise RuntimeError("Failed to create database table")


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
                   COALESCE(up.telegram_name, '') as telegram_name
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
                   COALESCE(up.telegram_name, '') as telegram_name
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
