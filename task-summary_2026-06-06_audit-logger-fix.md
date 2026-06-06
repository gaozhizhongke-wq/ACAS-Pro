# ACAS-Pro AuditLogger & Schema Fix

**Date:** 2026-06-06
**Objective:** Fix critical bugs in ACAS-Pro core modules identified from prior review

## Bugs Fixed

### 1. AuditLogger INSERT column mismatch (Critical)
- **File:** `src/acas_pro/core/logging.py`
- **Problem:** `AuditLogger.log()` used raw SQL `INSERT INTO audit_logs (timestamp, event_type, user_id, ip_address, details, severity)` — none of these columns matched the actual `audit_logs` schema (`id, user_id, action, resource_type, resource_id, details, ip_address, user_agent, created_at`). Every audit write silently failed (caught by try/except).
- **Fix:** Replaced raw SQL with `db.insert("audit_logs", {...})` using correct column names. Added `severity` column to schema. Extracts `resource_type`, `resource_id`, `user_agent` from details dict when available.

### 2. Missing `severity` column in audit_logs schema
- **File:** `src/acas_pro/core/database.py`
- **Problem:** Original code intended to store severity but the column didn't exist in either SQLite or PostgreSQL schema.
- **Fix:** Added `severity TEXT DEFAULT 'info'` to both SQLite and PostgreSQL CREATE TABLE statements.

### 3. Missing `Any` import in health.py
- **File:** `src/acas_pro/web/health.py`
- **Problem:** `from typing import Dict, List, Optional` — missing `Any` which was used in type annotations.
- **Fix:** Added `Any` to the typing imports.

## Test Results
- All 2345 tests pass, 18 skipped
- Coverage: 78.81% (above 78% threshold)
- Commit: `be44925`
