import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

try:
    from config.config import DATABASE_PATH
    DB_FILE = Path(DATABASE_PATH)
except ImportError:
    # Fallback if config not available
    DB_FILE = Path(__file__).parent.parent.parent / "data" / "races.db"


def _get_conn():
    return sqlite3.connect(DB_FILE)


def clear_db():
    """Полностью очищает базу данных"""
    with _get_conn() as conn:
        # Удаляем все таблицы
        conn.execute("DROP TABLE IF EXISTS user_races")
        conn.execute("DROP TABLE IF EXISTS user_competitors")
        conn.commit()


def init_db():
    """Ensure SQLite schema exists."""
    with _get_conn() as conn:
        # Удаляем старую таблицу если она есть
        conn.execute("DROP TABLE IF EXISTS user_races")
        
        # Таблица для полной информации о конкурентах
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
                PRIMARY KEY (user_id, date, race_number, num)
            )
            """
        )
        conn.commit()





def save_competitor(user_id: int, date: str, race_number: str, race_href: str, competitor_data: Dict[str, Any]) -> bool:
    """Insert competitor data for user; return True if inserted, False if duplicate."""
    try:
        # Сериализуем lap_times в JSON
        lap_times_json = json.dumps([
            {
                'lap_number': lap.lap_number,
                'lap_time': lap.lap_time,
                'sector1': lap.sector1,
                'sector2': lap.sector2,
                'sector3': lap.sector3,
                'sector4': lap.sector4
            } for lap in competitor_data.get('lap_times', [])
        ]) if competitor_data.get('lap_times') else None
        
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO user_competitors (
                    user_id, date, race_number, race_href, competitor_id, num, name, pos, laps,
                    theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
                    lap_times_json
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
                   theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json
            FROM user_competitors 
            WHERE user_id=? 
            ORDER BY date DESC
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
                   theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json
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
                   theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json
            FROM user_competitors 
            ORDER BY date DESC
            """,
        )
        return cur.fetchall()


def _time_string_to_ms(time_str: str) -> int:
    """Преобразует строку времени 'M:SS.sss' в миллисекунды для сортировки"""
    if not time_str or time_str == "-":
        return 999999999  # Большое число для сортировки в конец
    
    try:
        # Убираем лишние пробелы
        time_str = time_str.strip()
        
        # Парсим формат M:SS.sss или MM:SS.sss
        if ':' in time_str and '.' in time_str:
            time_parts = time_str.split(':')
            minutes = int(time_parts[0])
            
            sec_ms_parts = time_parts[1].split('.')
            seconds = int(sec_ms_parts[0])
            milliseconds = int(sec_ms_parts[1])
            
            return minutes * 60000 + seconds * 1000 + milliseconds
        else:
            return 999999999
    except:
        return 999999999


def get_best_competitors(limit: int = 20):
    """Get best competitors sorted by best lap time (one per user)."""
    with _get_conn() as conn:
        cur = conn.execute(
            """
            SELECT user_id, date, race_number, num, name, display_name, theor_lap, theor_lap_formatted, best_lap, pos
            FROM user_competitors 
            WHERE best_lap IS NOT NULL AND best_lap != '' AND best_lap != '-'
            """,
        )
        results = cur.fetchall()
        
        # Группируем по user_id и находим лучшее время для каждого пользователя
        user_best = {}
        for result in results:
            user_id = result[0]
            best_lap = result[8]
            best_lap_ms = _time_string_to_ms(best_lap)
            
            if user_id not in user_best or best_lap_ms < _time_string_to_ms(user_best[user_id][8]):
                user_best[user_id] = result
        
        # Сортируем по времени лучшего круга
        sorted_results = sorted(user_best.values(), key=lambda x: _time_string_to_ms(x[8]))
        
        return sorted_results[:limit]


def get_best_competitors_today(today_date: str, limit: int = 20):
    """Get best competitors for today sorted by best lap time (one per user)."""
    with _get_conn() as conn:
        cur = conn.execute(
            """
            SELECT user_id, date, race_number, num, name, display_name, theor_lap, theor_lap_formatted, best_lap, pos
            FROM user_competitors 
            WHERE date = ? AND best_lap IS NOT NULL AND best_lap != '' AND best_lap != '-'
            """,
            (today_date,),
        )
        results = cur.fetchall()
        
        # Группируем по user_id и находим лучшее время для каждого пользователя
        user_best = {}
        for result in results:
            user_id = result[0]
            best_lap = result[8]
            best_lap_ms = _time_string_to_ms(best_lap)
            
            if user_id not in user_best or best_lap_ms < _time_string_to_ms(user_best[user_id][8]):
                user_best[user_id] = result
        
        # Сортируем по времени лучшего круга
        sorted_results = sorted(user_best.values(), key=lambda x: _time_string_to_ms(x[8]))
        
        return sorted_results[:limit] 