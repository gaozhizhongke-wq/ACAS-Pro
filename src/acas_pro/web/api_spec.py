"""API documentation registration (OpenAPI/Swagger)."""

from flask import Blueprint, jsonify

# ---------------------------------------------------------------------------
# OpenAPI 3.0 spec for ACAS Pro
# ---------------------------------------------------------------------------

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "ACAS Pro API",
        "description": "ACAS Pro - AI Content & Account Management Platform API",
        "version": "1.0.0",
        "contact": {"email": "support@acas-pro.com"},
    },
    "servers": [{"url": "/api", "description": "API Server"}],
    "tags": [
        {"name": "auth", "description": "Authentication endpoints"},
        {"name": "dashboard", "description": "Dashboard & statistics"},
        {"name": "llm", "description": "LLM & AI features"},
        {"name": "metrics", "description": "Prometheus metrics"},
    ],
    "paths": {
        "/auth/register": {
            "post": {
                "tags": ["auth"],
                "summary": "Register a new user",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RegisterRequest"}
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Registration successful"},
                    "400": {"description": "Invalid input"},
                    "409": {"description": "User already exists"},
                },
            }
        },
        "/auth/login": {
            "post": {
                "tags": ["auth"],
                "summary": "Login user",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/LoginRequest"}
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Login successful, returns JWT"},
                    "401": {"description": "Invalid credentials"},
                },
            }
        },
        "/dashboard/stats": {
            "get": {
                "tags": ["dashboard"],
                "summary": "Get dashboard statistics",
                "security": [{"bearerAuth": []}],
                "responses": {
                    "200": {"description": "Dashboard stats"},
                    "401": {"description": "Unauthorized"},
                },
            }
        },
        "/llm/chat": {
            "post": {
                "tags": ["llm"],
                "summary": "Chat with LLM",
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ChatRequest"}
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Chat response"},
                    "401": {"description": "Unauthorized"},
                },
            }
        },
        "/metrics": {
            "get": {
                "tags": ["metrics"],
                "summary": "Prometheus metrics endpoint",
                "responses": {
                    "200": {"description": "Metrics in Prometheus format"},
                    "503": {"description": "prometheus_client not installed"},
                },
            }
        },
    },
    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        },
        "schemas": {
            "RegisterRequest": {
                "type": "object",
                "required": ["account", "password"],
                "properties": {
                    "account": {"type": "string", "description": "Account name (3-50 chars)"},
                    "password": {"type": "string", "format": "password", "description": "Password (8-128 chars, requires uppercase, lowercase, digit, special char)"},
                    "nickname": {"type": "string", "description": "Display name (optional)"},
                },
            },
            "LoginRequest": {
                "type": "object",
                "required": ["account", "password"],
                "properties": {
                    "account": {"type": "string", "description": "Account name"},
                    "password": {"type": "string", "format": "password"},
                },
            },
            "ChatRequest": {
                "type": "object",
                "required": ["message"],
                "properties": {
                    "message": {"type": "string"},
                    "conversation_id": {"type": "string"},
                },
            },
        },
    },
    "security": [{"bearerAuth": []}],
}


# ---------------------------------------------------------------------------
# Blueprint for API docs
# ---------------------------------------------------------------------------

docs_bp = Blueprint("api_docs", __name__, url_prefix="/api/docs")


@docs_bp.route("", methods=["GET"])
def swagger_ui() -> None:
    """Serve Swagger UI HTML with embedded resources (no external CDN)."""
    # Note: For production, serve swagger-ui-dist from static files instead.
    # This inline version avoids external CDN dependency for security.
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>ACAS Pro API - Swagger UI</title>
        <style>
            /* Minimal inline styles for basic Swagger UI display */
            body { margin: 0; padding: 20px; font-family: sans-serif; background: #fafafa; }
            .container { max-width: 1200px; margin: 0 auto; }
            .endpoint { background: white; padding: 15px; margin: 10px 0; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .method-get { color: #61affe; font-weight: bold; }
            .method-post { color: #49cc90; font-weight: bold; }
            .method-put { color: #fca130; font-weight: bold; }
            .method-delete { color: #f93e3e; font-weight: bold; }
            .path { font-family: monospace; font-size: 16px; }
            .description { color: #666; margin-top: 5px; }
            .auth-badge { background: #4990e2; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; }
            h1 { color: #3b4151; }
            pre { background: #f4f4f4; padding: 10px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>ACAS Pro API Documentation</h1>
            <p><a href="/api/openapi.json">OpenAPI JSON Spec</a> | <a href="/api/openapi.yaml">OpenAPI YAML Spec</a></p>
            <div id="endpoints"></div>
        </div>
        <script>
            fetch('/api/openapi.json')
                .then(r => r.json())
                .then(spec => {
                    const container = document.getElementById('endpoints');
                    for (const [path, methods] of Object.entries(spec.paths || {})) {
                        for (const [method, details] of Object.entries(methods)) {
                            const div = document.createElement('div');
                            div.className = 'endpoint';
                            const methodClass = `method-${method}`;
                            const authBadge = details.security ? '<span class=\"auth-badge\">🔐 Auth</span>' : '';
                            div.innerHTML = `
                                <div><span class=\"${methodClass}\">${method.toUpperCase()}</span> <span class=\"path\">${path}</span> ${authBadge}</div>
                                <div class=\"description\">${details.summary || ''}</div>
                            `;
                            container.appendChild(div);
                        }
                    }
                })
                .catch(err => console.error('Failed to load OpenAPI spec:', err));
        </script>
    </body>
    </html>
    """
    return html, 200, {"Content-Type": "text/html"}


# ---------------------------------------------------------------------------
# Register function
# ---------------------------------------------------------------------------


def register_api_docs(app) -> None:
    """Register API documentation endpoints.

    Adds:
    - /api/docs - Swagger UI
    - /api/openapi.json - OpenAPI spec (JSON)
    - /api/openapi.yaml - OpenAPI spec (YAML)
    """

    @app.route("/api/openapi.json", methods=["GET"])
    def openapi_json() -> None:
        return jsonify(OPENAPI_SPEC)

    @app.route("/api/openapi.yaml", methods=["GET"])
    def openapi_yaml() -> None:
        try:
            import yaml
        except ImportError:
            return jsonify(
                {"error": "YAML serialization unavailable — PyYAML not installed"}
            ), 503
        yaml_str = yaml.dump(OPENAPI_SPEC, default_flow_style=False, allow_unicode=True)
        return yaml_str, 200, {"Content-Type": "application/yaml"}

    app.register_blueprint(docs_bp)
    app.logger.info("API documentation registered at /api/docs")
