#!/usr/bin/env python3
"""
Миграция данных из SQLite → PostgreSQL (Supabase).
Запуск: python scripts/migrate_sqlite_to_pg.py
"""
import sys
import os
import sqlite3
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config.config import DATABASE_URL, DATABASE_PATH

SQLITE_FILE = DATABASE_PATH


def migrate():
    if not os.path.exists(SQLITE_FILE):
        print(f"❌ SQLite файл не найден: {SQLITE_FILE}")
        sys.exit(1)

    if not DATABASE_URL:
        print("❌ DATABASE_URL не задан в .env")
        sys.exit(1)

    print(f"📂 Читаю данные из SQLite: {SQLITE_FILE}")
    sqlite_conn = sqlite3.connect(SQLITE_FILE)
    rows = sqlite_conn.execute(
        """
        SELECT user_id, date, race_number, race_href, competitor_id, num, name, pos, laps,
               theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name,
               gap_to_leader, lap_times_json, best_lap_ms
        FROM user_competitors
        """
    ).fetchall()
    sqlite_conn.close()

    print(f"📊 Найдено записей: {len(rows)}")
    if not rows:
        print("ℹ️  Нет данных для миграции")
        return

    print(f"🔌 Подключаюсь к PostgreSQL...")
    pg_conn = psycopg2.connect(DATABASE_URL)
    cur = pg_conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_competitors (
            user_id BIGINT,
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

    inserted = 0
    skipped = 0
    for row in rows:
        try:
            cur.execute(
                """
                INSERT INTO user_competitors (
                    user_id, date, race_number, race_href, competitor_id, num, name, pos, laps,
                    theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name,
                    gap_to_leader, lap_times_json, best_lap_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (user_id, date, race_number, num) DO NOTHING
                """,
                row,
            )
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"⚠️  Ошибка при вставке строки {row[:3]}: {e}")

    pg_conn.commit()
    pg_conn.close()

    print(f"✅ Готово! Вставлено: {inserted}, пропущено (дубли): {skipped}")


if __name__ == "__main__":
    migrate()
