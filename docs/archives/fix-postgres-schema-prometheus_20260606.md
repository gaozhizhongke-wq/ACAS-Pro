# Fix: _get_postgres_schema extraction + Prometheus registry + test suite green

**Time:** 2026-06-06 09:02 GMT+8
**Commit:** 397e63d

## Objective
Fix the `_get_postgres_schema` AttributeError and Prometheus metrics registration conflicts that caused 10 test failures and waitress 500 errors.

## Key Changes

### 1. database.py — `_get_postgres_schema` extraction
- PostgreSQL schema was **dead code** inside `_get_sqlite_schema()` (placed after the `return` statement with a stray docstring)
- Extracted into a proper `_get_postgres_schema()` method on `DatabaseManager`
- This was the root cause of `DatabaseManager has no attribute '_get_postgres_schema'` at startup

### 2. metrics.py — Prometheus registry isolation
- Module-level `Counter`/`Histogram`/`Gauge`/`Info` registrations used the global `CollectorRegistry`, causing `ValueError: Duplicated timeseries` when `create_app()` was called multiple times (test suite)
- Rewrote to use a **dedicated `CollectorRegistry`** with lazy initialization (`_init_metrics()`)
- Added graceful fallback: returns 503 if `prometheus_client` not installed

### 3. prometheus_client dependency
- Was missing from the environment; installed via pip

## Test Results
- **Before:** 17 failed, 13 errors, 2315 passed
- **After:** **2345 passed, 0 failed, 18 skipped** ✅
