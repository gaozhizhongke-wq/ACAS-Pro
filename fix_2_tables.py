#!/usr/bin/env python3
"""Create data_alerts and festivals in PostgreSQL with correct BOOLEAN defaults, then migrate data."""
import sqlite3
import psycopg2
import os

SQLITE_PATH = os.path.expanduser('~/.acas-pro/data/acas.db')
PG_DSN = "host=localhost port=5432 dbname=acas_pro user=acas_user password=acas_secure_pass_2026"

CREATE_DATA_ALERTS = """
CREATE TABLE IF NOT EXISTS data_alerts (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_type TEXT NOT NULL,
    platform TEXT,
    account_id TEXT,
    content_id TEXT,
    message TEXT,
    severity TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by TEXT
);
"""

CREATE_FESTIVALS = """
CREATE TABLE IF NOT EXISTS festivals (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_en TEXT,
    festival_type TEXT,
    markets TEXT,
    month INTEGER,
    day INTEGER,
    lunar BOOLEAN DEFAULT FALSE,
    floating BOOLEAN DEFAULT FALSE,
    floating_rule TEXT,
    importance INTEGER DEFAULT 3,
    duration_days INTEGER DEFAULT 1,
    pre_heat_days INTEGER DEFAULT 7,
    themes TEXT,
    keywords TEXT,
    visual_style TEXT,
    content_tips TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def main():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    pg_conn = psycopg2.connect(PG_DSN)
    pg_cur = pg_conn.cursor()

    # Create tables
    print("=== Creating tables ===")
    pg_cur.execute("DROP TABLE IF EXISTS data_alerts CASCADE")
    pg_cur.execute(CREATE_DATA_ALERTS)
    print("  data_alerts: created")

    pg_cur.execute("DROP TABLE IF EXISTS festivals CASCADE")
    pg_cur.execute(CREATE_FESTIVALS)
    print("  festivals: created")
    pg_conn.commit()

    # Migrate data_alerts
    print("\n=== Migrating data_alerts ===")
    sq_cur = sqlite_conn.cursor()
    sq_cur.execute("SELECT * FROM data_alerts")
    rows = sq_cur.fetchall()
    col_names = [desc[0] for desc in sq_cur.description]
    print(f"  SQLite columns: {col_names}")

    count = 0
    for row in rows:
        # Convert acknowledged (0/1) to boolean
        converted = list(row)
        # Find index of 'acknowledged' column
        for i, c in enumerate(col_names):
            if c == 'acknowledged':
                converted[i] = bool(row[i]) if row[i] is not None else False
        try:
            placeholders = ', '.join(['%s'] * len(converted))
            col_list = ', '.join(f'"{c}"' for c in col_names)
            pg_cur.execute(
                f'INSERT INTO data_alerts ({col_list}) VALUES ({placeholders})',
                tuple(converted)
            )
            count += 1
        except Exception as e:
            print(f"  Row error: {e}")
            break
    pg_conn.commit()
    print(f"  data_alerts: {count} rows migrated")

    # Migrate festivals
    print("\n=== Migrating festivals ===")
    sq_cur.execute("SELECT * FROM festivals")
    rows = sq_cur.fetchall()
    col_names = [desc[0] for desc in sq_cur.description]
    print(f"  SQLite columns: {col_names}")

    bool_cols = {'lunar', 'floating', 'is_active'}
    count = 0
    for row in rows:
        converted = list(row)
        for i, c in enumerate(col_names):
            if c in bool_cols and row[i] is not None:
                converted[i] = bool(row[i])
        try:
            placeholders = ', '.join(['%s'] * len(converted))
            col_list = ', '.join(f'"{c}"' for c in col_names)
            pg_cur.execute(
                f'INSERT INTO festivals ({col_list}) VALUES ({placeholders})',
                tuple(converted)
            )
            count += 1
        except Exception as e:
            print(f"  Row error: {e}")
            break
    pg_conn.commit()
    print(f"  festivals: {count} rows migrated")

    sqlite_conn.close()
    pg_cur.close()
    pg_conn.close()
    print("\n=== Done ===")

if __name__ == '__main__':
    main()
