# ADR 002: SQLite for Development, PostgreSQL for Production

## Status
Accepted

## Context
ACAS Pro needs a database solution that works for:
- Development: Easy setup, no external dependencies
- Production: High performance, concurrency, reliability

## Decision
We will use:
- **Development/Testing**: SQLite (file-based, zero configuration)
- **Production**: PostgreSQL (enterprise-grade, scalable)

The DatabaseManager abstraction allows seamless switching via `DATABASE_URL` environment variable.

## Consequences

### Positive
- Developer experience: SQLite requires no setup
- Production performance: PostgreSQL handles concurrent connections
- Flexibility: Same code works with both databases
- Testing: SQLite in-memory for fast test execution

### Negative
- Feature parity: Some PostgreSQL features not available in SQLite
- Migration complexity: Schema changes must work with both
- Testing gap: SQLite behavior may differ from PostgreSQL

## Mitigations
- Use standard SQL compatible with both databases
- Test against PostgreSQL in CI/CD pipeline
- Document PostgreSQL-specific features

## Implementation
See `src/acas_pro/core/database.py` for DatabaseManager implementation.

## References
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
