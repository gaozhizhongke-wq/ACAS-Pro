# Security Fixes Round 2 — 2026-06-04

## Objective
Continue fixing security issues in ACAS Pro: eliminate FLASK_ENV references, fix missing SECRET_KEY in web_app.py, remove CSRF_STATE_SECRET random fallback.

## Key Changes
1. **web_app.py**: Added SECRET_KEY configuration — reads from `SECRET_KEY` env or `config().security.secret_key`. Raises ValueError if missing/weak in all environments.
2. **wsgi.py**: `FLASK_ENV` → `ACAS_ENV` for environment detection consistency.
3. **core/security.py**: `CSRF_STATE_SECRET` — removed silent `secrets.token_hex(32)` fallback; now logs warning if unset (constant was unused anyway).
4. **tests/**: All `FLASK_ENV` references replaced with `ACAS_ENV` (e2e_playwright/conftest.py, unit/test_security.py).
5. **SECURITY_FIXES_2026-06-04.md**: Updated with fixes #9-#12.

## Verification
- `FLASK_ENV` completely eliminated from entire codebase (0 grep hits)
- All modified files pass syntax check
- Tests cannot run on Windows due to pre-existing `fcntl` import issue (not introduced by these changes)

## Conclusions
All known environment variable inconsistencies and SECRET_KEY gaps are now resolved. Remaining issue: `fcntl` module (Linux-only) imported in security.py prevents testing on Windows.
