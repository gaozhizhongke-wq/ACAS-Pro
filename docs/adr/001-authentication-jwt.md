# ADR 001: JWT-Based Authentication

## Status
Accepted

## Context
ACAS Pro requires a secure authentication mechanism for API access. The system needs to support:
- Stateless authentication for scalability
- Token expiration and refresh
- Protection against common attacks (replay, theft)

## Decision
We will use JWT (JSON Web Tokens) with the following configuration:
- Access tokens: 15-minute expiration
- Refresh tokens: 7-day expiration
- HS256 algorithm with strong secret key
- Token revocation via jti (JWT ID) blacklist

## Consequences

### Positive
- Stateless: No server-side session storage required
- Scalable: Works well with multiple application instances
- Standard: Widely supported and understood
- Flexible: Can carry claims/permissions in payload

### Negative
- Token size: JWTs are larger than session IDs
- Revocation complexity: Requires blacklist for immediate revocation
- Secret management: Compromised secret affects all tokens

## Alternatives Considered

### Session-Based Authentication
- **Pros**: Immediate revocation, smaller token size
- **Cons**: Requires shared session store (Redis), harder to scale horizontally
- **Decision**: Rejected in favor of stateless JWT

### OAuth 2.0 / OpenID Connect
- **Pros**: Industry standard, third-party integration
- **Cons**: Overkill for internal API, adds complexity
- **Decision**: Rejected for simplicity

## Implementation
See `src/acas_pro/core/security.py` for JWTManager implementation.

## References
- [RFC 7519 - JSON Web Token](https://tools.ietf.org/html/rfc7519)
- [OWASP JWT Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
