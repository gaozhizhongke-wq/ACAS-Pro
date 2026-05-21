#!/usr/bin/env python3
"""Fix boolean columns in 3 failed tables and re-migrate them."""
import sqlite3
import psycopg2
import os

SQLITE_PATH = os.path.expanduser('~/.acas-pro/data/acas.db')
PG_DSN = "host=localhost port=5432 dbname=acas_pro user=acas_user password=acas_secure_pass_2026"

BOOLEAN_TABLES = {
    'account_login_logs': ['success'],
    'data_alerts': ['acknowledged'],
    'festivals': ['lunar', 'global'],
}

def main():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    pg_conn = psycopg2.connect(PG_DSN)
    pg_cur = pg_conn.cursor()

    for table, bool_cols in BOOLEAN_TABLES.items():
        print(f"\n=== Fixing {table} ===")
        # Get SQLite data
        sq_cur = sqlite_conn.cursor()
        sq_cur.execute(f'SELECT * FROM "{table}"')
        rows = sq_cur.fetchall()

        # Get column names
        sq_cur.execute(f'PRAGMA table_info("{table}")')
        col_info = sq_cur.fetchall()
        col_names = [c[1] for c in col_info]

        # Clear PostgreSQL table
        pg_cur.execute(f'TRUNCATE TABLE "{table}" CASCADE')
        print(f"  Truncated {table}")

        # Build INSERT with boolean conversion
        col_placeholders = ', '.join(f'"{c}"' for c in col_names)
        placeholders = ', '.join(['%s'] * len(col_names))

        count = 0
        for row in rows:
            # Convert boolean columns: 0/1 -> False/True
            converted = []
            for i, val in enumerate(row):
                col_name = col_names[i]
                if col_name in bool_cols and isinstance(val, int):
                    converted.append(bool(val))
                else:
                    converted.append(val)
            try:
                pg_cur.execute(
                    f'INSERT INTO "{table}" ({col_placeholders}) VALUES ({placeholders})',
                    tuple(converted)
                )
                count += 1
            except Exception as e:
                print(f"  Row error: {e}")

        pg_conn.commit()
        print(f"  {table}: {count} rows migrated")

    sqlite_conn.close()
    pg_cur.close()
    pg_conn.close()
    print("\n=== Fix Complete ===")

if __name__ == '__main__':
    main()
