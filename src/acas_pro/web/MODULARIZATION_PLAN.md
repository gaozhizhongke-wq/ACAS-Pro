# ACAS Pro Web - Modularization Plan (P10)

## Current State
- `web_app.py`: 1275 lines
  - Python routes: ~560 lines
  - HTML template (DASHBOARD_HTML): ~697 lines
  - Mixed concerns: auth, LLM, dashboard, products, festivals, etc.

## Target Structure

```
src/acas_pro/web/
├── __init__.py              # Flask app factory
├── config.py                # App configuration
├── middleware.py            # Auth, CORS, rate limiting
├── templates/
│   └── dashboard.html       # Extracted HTML template
├── static/
│   ├── css/
│   └── js/
└── routes/
    ├── __init__.py          # Blueprint registration
    ├── auth.py              # /api/auth/* (DONE)
    ├── llm.py               # /api/llm/* (DONE - partial)
    ├── dashboard.py         # /api/dashboard/*, /
    ├── products.py          # /api/products/*
    ├── festivals.py         # /api/festivals
    ├── accounts.py          # /api/accounts
    └── forecast.py          # /api/forecast/*
```

## Implementation Status

| Route File | Status | Routes Covered |
|------------|--------|----------------|
| auth.py | ✅ Done | /api/auth/register, /api/auth/login, /api/auth/me |
| llm.py | ✅ Done | /api/llm/config, /api/llm/chat |
| dashboard.py | 🚧 TODO | /api/dashboard/stats, /api/health, / |
| products.py | 🚧 TODO | /api/products, /api/products/low-stock |
| festivals.py | 🚧 TODO | /api/festivals |
| accounts.py | 🚧 TODO | /api/accounts |
| forecast.py | 🚧 TODO | /api/forecast/daily |

## Migration Steps

1. **Phase 1** (Current): Create route blueprints structure
   - ✅ auth.py - Authentication routes
   - ✅ llm.py - LLM configuration and chat
   - ✅ Basic app factory structure

2. **Phase 2**: Extract remaining API routes
   - dashboard.py - Dashboard stats and health check
   - products.py - Product management
   - festivals.py - Festival calendar
   - accounts.py - Account management
   - forecast.py - Sales forecasting

3. **Phase 3**: Extract HTML template
   - Move DASHBOARD_HTML to templates/dashboard.html
   - Use Flask's render_template() instead of render_template_string()

4. **Phase 4**: Update main web_app.py
   - Import and register all blueprints
   - Or switch to using the new app factory

## Backward Compatibility

The modularization maintains full backward compatibility:
- All route URLs remain the same
- All request/response formats remain the same
- JWT tokens remain valid
- Database schema unchanged

## Testing Strategy

Before deploying modularized version:
1. Run all existing API tests
2. Verify auth flow (register, login, token refresh)
3. Verify LLM chat functionality
4. Verify dashboard loads correctly
5. Verify all CRUD operations work

## Notes

- Original `web_app.py` should be kept as backup until full migration is tested
- The modular structure allows for easier unit testing of individual route modules
- Each blueprint can have its own before_request handlers for specific auth requirements
