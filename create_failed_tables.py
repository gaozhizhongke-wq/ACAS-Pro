#!/usr/bin/env python3
"""Get SQLite CREATE TABLE for 3 failed tables, convert to PostgreSQL, and create them."""
import sqlite3
import psycopg2
import os
import re

SQLITE_PATH = os.path.expanduser('~/.acas-pro/data/acas.db')
PG_DSN = "host=localhost port=5432 dbname=acas_pro user=acas_user password=acas_secure_pass_2026"

TABLES = ['account_login_logs', 'data_alerts', 'festivals']

def get_sqlite_schema(sqlite_conn, table):
    cur = sqlite_conn.cursor()
    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    row = cur.fetchone()
    return row[0] if row else None

def sqlite_to_pg_create(sqlite_sql):
    """Convert SQLite CREATE TABLE to PostgreSQL CREATE TABLE."""
    # Remove SQLite-specific syntax
    sql = sqlite_sql

    # Replace AUTOINCREMENT with nothing (PostgreSQL uses SERIAL/GENERATED)
    sql = re.sub(r'\s+AUTOINCREMENT', '', sql, flags=re.IGNORECASE)

    # Replace SQLite types with PostgreSQL types
    type_map = {
        r'\bINTEGER\b': 'INTEGER',
        r'\bTEXT\b': 'TEXT',
        r'\bREAL\b': 'FLOAT',
        r'\bBLOB\b': 'BYTEA',
        r'\bNUMERIC\b': 'NUMERIC',
        r'\bBOOLEAN\b': 'BOOLEAN',
        r'\bDATETIME\b': 'TIMESTAMP',
        r'\bTIMESTAMP\b': 'TIMESTAMP',
        r'\bDATE\b': 'DATE',
        r'\bVARCHAR\(\d+\)': 'TEXT',
        r'\bNVARCHAR\(\d+\)': 'TEXT',
        r'\bFLOAT\b': 'FLOAT',
        r'\bDOUBLE\b': 'FLOAT',
        r'\bINT\b': 'INTEGER',
        r'\bCHAR\(\d+\)': 'TEXT',
    }
    for pattern, pg_type in type_map.items():
        sql = re.sub(pattern, pg_type, sql, flags=re.IGNORECASE)

    # Replace " with '
    # Actually, PostgreSQL uses double quotes for identifiers, so keep them

    return sql

def main():
    print("=== Creating 3 failed tables in PostgreSQL ===")

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    pg_conn = psycopg2.connect(PG_DSN)
    pg_cur = pg_conn.cursor()

    for table in TABLES:
        print(f"\n=== {table} ===")
        sqlite_sql = get_sqlite_schema(sqlite_conn, table)
        if not sqlite_sql:
            print(f"  ERROR: CREATE TABLE not found in SQLite")
            continue

        print(f"  SQLite SQL: {sqlite_sql[:200]}...")

        pg_sql = sqlite_to_pg_create(sqlite_sql)
        print(f"  PostgreSQL SQL: {pg_sql[:200]}...")

        try:
            pg_cur.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
            pg_cur.execute(pg_sql)
            pg_conn.commit()
            print(f"  Table created successfully")
        except Exception as e:
            print(f"  ERROR creating table: {e}")
            pg_conn.rollback()

    sqlite_conn.close()
    pg_cur.close()
    pg_conn.close()
    print("\n=== Done ===")

if __name__ == '__main__':
    main()
