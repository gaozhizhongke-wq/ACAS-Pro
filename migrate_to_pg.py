#!/usr/bin/env python3
"""
Migrate ACAS-Pro data from SQLite to PostgreSQL.
Reads schema + data from data/acas.db, creates tables and inserts into PostgreSQL.
"""
import sqlite3
import psycopg2
import os
import sys

SQLITE_PATH = os.path.expanduser('~/.acas-pro/data/acas.db')
PG_DSN = "host=localhost port=5432 dbname=acas_pro user=acas_user password=acas_secure_pass_2026"

# Type mapping: SQLite -> PostgreSQL
SQLITE_TO_PG = {
    'INTEGER': 'INTEGER',
    'TEXT': 'TEXT',
    'REAL': 'FLOAT',
    'BLOB': 'BYTEA',
    'NUMERIC': 'NUMERIC',
    'BOOLEAN': 'BOOLEAN',
    'DATETIME': 'TIMESTAMP',
    'TIMESTAMP': 'TIMESTAMP',
    'DATE': 'DATE',
    'VARCHAR': 'TEXT',
    'NVARCHAR': 'TEXT',
    'FLOAT': 'FLOAT',
    'DOUBLE': 'FLOAT',
    'INT': 'INTEGER',
    'CHAR': 'TEXT',
}

def normalize_type(sqlite_type):
    """Convert SQLite column type to PostgreSQL type."""
    upper = sqlite_type.strip().upper()
    for k, v in SQLITE_TO_PG.items():
        if upper.startswith(k):
            return v
    return 'TEXT'

def get_sqlite_schema(sqlite_conn):
    """Get table names and CREATE TABLE statements from SQLite."""
    cur = sqlite_conn.cursor()
    cur.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )
    return {row[0]: row[1] for row in cur.fetchall()}

def get_pg_columns(sqlite_conn, table):
    """Get column info for a SQLite table."""
    cur = sqlite_conn.cursor()
    cur.execute(f'PRAGMA table_info("{table}")')
    return cur.fetchall()  # (cid, name, type, notnull, dflt_value, pk)

def create_table_pg(pg_cur, table, columns):
    """Create a table in PostgreSQL from SQLite column info."""
    col_defs = []
    pk_cols = []
    for cid, name, ctype, notnull, dflt, pk in columns:
        pg_type = normalize_type(ctype)
        col_def = f'"{name}" {pg_type}'
        if pk:
            pk_cols.append(name)
        if notnull:
            col_def += ' NOT NULL'
        col_defs.append(col_def)

    ddl = f'CREATE TABLE IF NOT EXISTS "{table}" (\n  ' + ',\n  '.join(col_defs)
    if pk_cols:
        pk_quoted = ', '.join(f'"{c}"' for c in pk_cols)
        ddl += f',\n  PRIMARY KEY ({pk_quoted})'
    ddl += '\n);'
    pg_cur.execute(ddl)

def copy_table_data(sqlite_conn, pg_conn, pg_cur, table, columns):
    """Copy all rows from SQLite to PostgreSQL."""
    col_names = [c[1] for c in columns]
    col_placeholders = ', '.join([f'"{c}"' for c in col_names])
    placeholders = ', '.join(['%s'] * len(col_names))

    # Read from SQLite
    sq_cur = sqlite_conn.cursor()
    sq_cur.execute(f'SELECT * FROM "{table}"')
    rows = sq_cur.fetchall()

    if not rows:
        print(f"  {table}: 0 rows (empty)")
        return 0

    # Insert into PostgreSQL
    insert_sql = f'INSERT INTO "{table}" ({col_placeholders}) VALUES ({placeholders})'
    count = 0
    for row in rows:
        try:
            pg_cur.execute(insert_sql, tuple(row))
            count += 1
        except Exception as e:
            print(f"  {table}: row insert error: {e}")
            # Try with ON CONFLICT DO NOTHING equivalent
            break

    pg_conn.commit()
    print(f"  {table}: {count} rows copied")
    return count

def main():
    print("=== ACAS-Pro SQLite → PostgreSQL Migration ===")
    print(f"SQLite: {SQLITE_PATH}")
    print(f"PostgreSQL: {PG_DSN.split('password=')[0]}password=***")

    if not os.path.exists(SQLITE_PATH):
        print(f"ERROR: SQLite DB not found: {SQLITE_PATH}")
        sys.exit(1)

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    pg_conn = psycopg2.connect(PG_DSN)
    pg_cur = pg_conn.cursor()

    # Get tables
    tables = get_sqlite_schema(sqlite_conn)
    print(f"\nFound {len(tables)} tables in SQLite.\n")

    total_rows = 0
    for table in sorted(tables.keys()):
        try:
            columns = get_pg_columns(sqlite_conn, table)
            if not columns:
                print(f"  {table}: skipping (no columns)")
                continue

            # Create table
            create_table_pg(pg_cur, table, columns)

            # Copy data
            n = copy_table_data(sqlite_conn, pg_conn, pg_cur, table, columns)
            total_rows += n
        except Exception as e:
            print(f"  {table}: ERROR: {e}")

    sqlite_conn.close()
    pg_cur.close()
    pg_conn.close()

    print(f"\n=== Migration Complete ===")
    print(f"Total rows copied: {total_rows}")

if __name__ == '__main__':
    main()
