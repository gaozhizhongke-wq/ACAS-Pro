# ACAS Pro Architecture

## System Overview

```mermaid
graph TB
    subgraph "Client Layer"
        Web[Web Browser]
        Mobile[Mobile App]
        API[API Clients]
    end

    subgraph "Infrastructure Layer"
        Nginx[Nginx Reverse Proxy]
        SSL[SSL/TLS Termination]
    end

    subgraph "Application Layer"
        Flask[Flask Application]
        Auth[Authentication<br/>JWT Manager]
        Routes[API Routes<br/>Blueprints]
        Middleware[Middleware<br/>Request Tracing]
    end

    subgraph "Service Layer"
        UserService[User Service]
        LLMService[LLM Service]
        AnalyticsService[Analytics Service]
        PublisherService[Publisher Service]
    end

    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL<br/>Production)]
        SQLite[(SQLite<br/>Development)]
        Redis[(Redis<br/>Cache/Session)]
    end

    subgraph "External Services"
        DeepSeek[DeepSeek API]
        OpenAI[OpenAI API]
        Anthropic[Anthropic API]
        Social[Social Media APIs]
    end

    Web --> Nginx
    Mobile --> Nginx
    API --> Nginx
    
    Nginx --> SSL
    SSL --> Flask
    
    Flask --> Auth
    Flask --> Middleware
    Flask --> Routes
    
    Routes --> UserService
    Routes --> LLMService
    Routes --> AnalyticsService
    Routes --> PublisherService
    
    UserService --> PostgreSQL
    UserService --> SQLite
    LLMService --> Redis
    
    LLMService --> DeepSeek
    LLMService --> OpenAI
    LLMService --> Anthropic
    PublisherService --> Social
```

## Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant Flask
    participant Auth as Auth Service
    participant DB as Database
    participant JWT as JWT Manager

    Client->>Flask: POST /api/auth/register
    Flask->>Auth: validate_password()
    Auth-->>Flask: password_valid
    Flask->>DB: create_user()
    DB-->>Flask: user_created
    Flask->>JWT: create_access_token()
    JWT-->>Flask: token
    Flask-->>Client: {token, user}

    Client->>Flask: POST /api/auth/login
    Flask->>Auth: verify_credentials()
    Auth->>DB: get_user()
    DB-->>Auth: user
    Auth-->>Flask: credentials_valid
    Flask->>JWT: create_access_token()
    JWT-->>Flask: token
    Flask-->>Client: {token, user}

    Client->>Flask: GET /api/auth/me
    Flask->>JWT: verify_token()
    JWT-->>Flask: payload
    Flask->>DB: get_user_by_id()
    DB-->>Flask: user
    Flask-->>Client: {user_id, account}
```

## Request Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant Nginx
    participant Flask
    participant Middleware
    participant Routes
    participant Service
    participant DB

    Client->>Nginx: HTTP Request
    Nginx->>Flask: Forward Request
    
    Flask->>Middleware: before_request
    Middleware->>Middleware: generate_request_id()
    Middleware->>Middleware: start_timer()
    Middleware-->>Flask: continue
    
    Flask->>Routes: route_handler
    Routes->>Service: business_logic
    Service->>DB: query/insert/update
    DB-->>Service: result
    Service-->>Routes: data
    Routes-->>Flask: response
    
    Flask->>Middleware: after_request
    Middleware->>Middleware: log_request()
    Middleware->>Middleware: add_headers()
    Middleware-->>Flask: response
    
    Flask-->>Nginx: HTTP Response
    Nginx-->>Client: HTTP Response
```

## Data Flow

```mermaid
flowchart LR
    subgraph "Input"
        User[User Input]
        Config[Configuration]
        API[External APIs]
    end

    subgraph "Processing"
        Validate[Validation Layer]
        Transform[Transform Layer]
        Business[Business Logic]
    end

    subgraph "Storage"
        Cache[Redis Cache]
        DB[(Database)]
        Files[File Storage]
    end

    subgraph "Output"
        Response[API Response]
        Webhook[Webhooks]
        Logs[Audit Logs]
    end

    User --> Validate
    Config --> Validate
    API --> Validate
    
    Validate --> Transform
    Transform --> Business
    
    Business --> Cache
    Business --> DB
    Business --> Files
    
    Business --> Response
    Business --> Webhook
    Business --> Logs
```

## Module Dependencies

```mermaid
graph TD
    WebApp[web_app.py] --> Config[config.py]
    WebApp --> Security[security.py]
    WebApp --> Database[database.py]
    WebApp --> Middleware[middleware.py]
    WebApp --> Health[health.py]
    WebApp --> Routes[routes/]
    
    Routes --> Auth[auth.py]
    Routes --> LLM[llm.py]
    Routes --> Dashboard[dashboard.py]
    
    Auth --> UserService[user_service.py]
    Auth --> JWT[JWTManager]
    Auth --> RateLimit[RateLimiter]
    
    LLM --> LLMClient[llm_client.py]
    LLM --> Config
    
    UserService --> Database
    UserService --> PasswordValidator[PasswordValidator]
    
    Middleware --> Logging[logging.py]
    Health --> Database
    Health --> Config
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Internet"
        Users[Users]
    end

    subgraph "Cloud Infrastructure"
        subgraph "Load Balancer"
            LB[HAProxy/Nginx]
        end

        subgraph "Application Servers"
            App1[ACAS Pro Instance 1]
            App2[ACAS Pro Instance 2]
            App3[ACAS Pro Instance 3]
        end

        subgraph "Data Layer"
            PG[(PostgreSQL Primary)]
            PG_R[(PostgreSQL Replica)]
            Redis1[Redis Cache]
            Redis2[Redis Session]
        end

        subgraph "Monitoring"
            Prometheus[Prometheus]
            Grafana[Grafana]
            Loki[Loki Logs]
        end
    end

    Users --> LB
    LB --> App1
    LB --> App2
    LB --> App3
    
    App1 --> PG
    App2 --> PG
    App3 --> PG
    
    PG --> PG_R
    
    App1 --> Redis1
    App2 --> Redis1
    App3 --> Redis1
    
    App1 --> Redis2
    App2 --> Redis2
    App3 --> Redis2
    
    App1 --> Prometheus
    App2 --> Prometheus
    App3 --> Prometheus
    
    Prometheus --> Grafana
    App1 --> Loki
    App2 --> Loki
    App3 --> Loki
```

## Security Layers

```mermaid
graph TB
    subgraph "Perimeter Security"
        WAF[Web Application Firewall]
        DDoS[DDoS Protection]
        SSL[SSL/TLS]
    end

    subgraph "Application Security"
        Auth[Authentication<br/>JWT]
        RBAC[Authorization<br/>RBAC]
        RateLimit[Rate Limiting]
    end

    subgraph "Data Security"
        Encrypt[Encryption<br/>at Rest]
        Hash[Password Hashing<br/>bcrypt]
        Mask[Data Masking]
    end

    subgraph "Operational Security"
        Audit[Audit Logging]
        Monitor[Security Monitoring]
        Scan[Vulnerability Scanning]
    end

    WAF --> Auth
    DDoS --> Auth
    SSL --> Auth
    
    Auth --> RBAC
    RBAC --> RateLimit
    
    RateLimit --> Encrypt
    RateLimit --> Hash
    RateLimit --> Mask
    
    Encrypt --> Audit
    Hash --> Audit
    Mask --> Audit
    
    Audit --> Monitor
    Monitor --> Scan
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.11+ |
| **Web Framework** | Flask 3.0+ |
| **Database** | PostgreSQL 16 / SQLite |
| **Cache** | Redis 7 |
| **Authentication** | JWT (PyJWT) |
| **Password Hashing** | bcrypt |
| **Encryption** | cryptography |
| **Validation** | Pydantic |
| **Testing** | pytest |
| **Documentation** | OpenAPI 3.0 |
| **Container** | Docker |
| **Orchestration** | Docker Compose |
| **CI/CD** | GitHub Actions |
| **Monitoring** | Prometheus + Grafana |

## Scalability Considerations

### Horizontal Scaling
- Stateless application servers
- Shared PostgreSQL database
- Redis for distributed caching
- Load balancer for traffic distribution

### Vertical Scaling
- Database read replicas
- Redis cluster mode
- Application server resources

### Caching Strategy
- Redis for session storage
- Application-level caching
- Database query caching

## Disaster Recovery

### Backup Strategy
- PostgreSQL: Continuous archiving + daily backups
- Redis: RDB snapshots
- Files: Incremental backups

### Recovery Time Objectives
- RTO: 1 hour
- RPO: 15 minutes

### Failover
- Database: Automatic failover to replica
- Application: Load balancer health checks
- Cache: Redis Sentinel for automatic failover
