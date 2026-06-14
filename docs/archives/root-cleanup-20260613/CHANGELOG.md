# Changelog

All notable changes to ACAS Pro will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Integration tests for API endpoints
- Architecture Decision Records (ADRs)
- Contributing guidelines
- This changelog

## [4.0.0] - 2026-05-10

### Added
- Comprehensive health check endpoint with database, configuration, and disk monitoring
- Request context middleware with X-Request-ID tracing
- Centralized error handling with consistent JSON responses
- OpenAPI 3.0.3 specification with Swagger UI at `/api/docs`
- Production middleware for structured logging
- CI/CD pipeline with GitHub Actions
- Unit tests for authentication, database, and health checks
- Makefile for common development tasks
- pyproject.toml with modern Python packaging configuration
- Docker multi-stage build optimization

### Changed
- Migrated to modular Flask blueprint architecture
- Unified JWT authentication system
- Enhanced password validation with complexity requirements
- Improved rate limiting for login and registration endpoints
- Updated health check to return proper HTTP status codes

### Fixed
- Fixed `db.update()` signature mismatch causing runtime crashes
- Fixed Python 3.11/3.14 environment compatibility issues
- Fixed `config.app.env` AttributeError
- Fixed products table schema mismatch
- Fixed duplicate JavaScript function definitions
- Fixed CORS handling for production environments
- Removed token from URL parameters (security)
- Removed dead bcrypt import

### Security
- Added brute-force protection for login (20 attempts / 10 min)
- Added rate limiting for registration (10 attempts / 10 min)
- Implemented security headers (CSP, HSTS, X-Frame-Options)
- Added input validation for SQL injection and XSS
- Enforced HTTPS warnings in production
- Removed sensitive files from git history
- Made encryption salt environment-dependent

## [3.0.0] - 2024-01-15

### Added
- LLM integration with multiple providers (OpenAI, Anthropic, DeepSeek)
- Multi-platform publishing capabilities
- Advanced analytics and forecasting
- Festival calendar integration

### Changed
- Major UI redesign
- Performance optimizations

## [2.0.0] - 2023-06-01

### Added
- Web dashboard
- User authentication system
- Database abstraction layer

### Changed
- Migrated from CLI to web interface

## [1.0.0] - 2023-01-01

### Added
- Initial release
- Basic content generation
- Single platform publishing

---

## Release Notes Template

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Now removed features

### Fixed
- Bug fixes

### Security
- Security improvements
```
