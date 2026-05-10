# ADR 003: Modular Web Architecture with Flask Blueprints

## Status
Accepted

## Context
The original `web_app.py` was a 1300-line monolithic file containing:
- Route handlers
- HTML templates
- Authentication logic
- LLM integration
- Dashboard functionality

This made the code difficult to maintain, test, and extend.

## Decision
We will refactor the web layer into a modular structure using Flask Blueprints:

```
src/acas_pro/web/
├── __init__.py          # App factory
├── middleware.py        # Request/response middleware
├── health.py            # Health check logic
├── api_spec.py          # OpenAPI specification
├── routes/
│   ├── auth.py          # Authentication routes
│   ├── llm.py           # LLM routes
│   └── dashboard.py     # Dashboard routes
```

## Consequences

### Positive
- Separation of concerns: Each module has single responsibility
- Testability: Can test routes in isolation
- Maintainability: Smaller files are easier to understand
- Extensibility: New features can add new blueprints

### Negative
- Initial refactoring effort
- More files to manage
- Need to understand Flask Blueprints

## Migration Strategy
1. Phase 1: Create blueprint structure alongside existing code
2. Phase 2: Extract routes one at a time
3. Phase 3: Update main app to use blueprints
4. Phase 4: Remove old monolithic code

## Current Status
Phase 1 complete: Core blueprints created, original web_app.py functional.

## Implementation
See `src/acas_pro/web/` directory for modular structure.

## References
- [Flask Blueprints Documentation](https://flask.palletsprojects.com/en/2.3.x/blueprints/)
