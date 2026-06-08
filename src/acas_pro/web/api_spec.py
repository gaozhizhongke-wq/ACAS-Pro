"""API documentation registration (OpenAPI/Swagger)."""

from flask import Blueprint, jsonify, send_from_directory, current_app
import os

# ---------------------------------------------------------------------------
# OpenAPI 3.0 spec for ACAS Pro
# ---------------------------------------------------------------------------

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "ACAS Pro API",
        "description": "ACAS Pro - AI Content & Account Management Platform API",
        "version": "1.0.0",
        "contact": {
            "email": "support@acas-pro.com"
        }
    },
    "servers": [
        {
            "url": "/api",
            "description": "API Server"
        }
    ],
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
                    }
                },
                "responses": {
                    "200": {"description": "Registration successful"},
                    "400": {"description": "Invalid input"},
                    "409": {"description": "User already exists"},
                }
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
                    }
                },
                "responses": {
                    "200": {"description": "Login successful, returns JWT"},
                    "401": {"description": "Invalid credentials"},
                }
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
                }
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
                    }
                },
                "responses": {
                    "200": {"description": "Chat response"},
                    "401": {"description": "Unauthorized"},
                }
            }
        },
        "/metrics": {
            "get": {
                "tags": ["metrics"],
                "summary": "Prometheus metrics endpoint",
                "responses": {
                    "200": {"description": "Metrics in Prometheus format"},
                    "503": {"description": "prometheus_client not installed"},
                }
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
                "required": ["username", "password", "account"],
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string", "format": "password"},
                    "account": {"type": "string"},
                }
            },
            "LoginRequest": {
                "type": "object",
                "required": ["username", "password"],
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string", "format": "password"},
                }
            },
            "ChatRequest": {
                "type": "object",
                "required": ["message"],
                "properties": {
                    "message": {"type": "string"},
                    "conversation_id": {"type": "string"},
                }
            },
        }
    },
    "security": [{"bearerAuth": []}],
}


# ---------------------------------------------------------------------------
# Blueprint for API docs
# ---------------------------------------------------------------------------

docs_bp = Blueprint('api_docs', __name__, url_prefix='/api/docs')


@docs_bp.route('', methods=['GET'])
def swagger_ui() -> None:
    """Serve Swagger UI HTML."""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>ACAS Pro API - Swagger UI</title>
        <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
            window.onload = function() {
                SwaggerUIBundle({
                    url: '/api/openapi.json',
                    dom_id: '#swagger-ui',
                    presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
                });
            };
        </script>
    </body>
    </html>
    """
    return html, 200, {'Content-Type': 'text/html'}


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
    @app.route('/api/openapi.json', methods=['GET'])
    def openapi_json() -> None:
        return jsonify(OPENAPI_SPEC)

    @app.route('/api/openapi.yaml', methods=['GET'])
    def openapi_yaml() -> None:
        try:
            import yaml
        except ImportError:
            return jsonify({'error': 'YAML serialization unavailable — PyYAML not installed'}), 503
        yaml_str = yaml.dump(OPENAPI_SPEC, default_flow_style=False, allow_unicode=True)
        return yaml_str, 200, {'Content-Type': 'application/yaml'}

    app.register_blueprint(docs_bp)
    app.logger.info("API documentation registered at /api/docs")
