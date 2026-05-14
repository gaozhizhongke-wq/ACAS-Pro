"""ACAS Pro Web - OpenAPI Specification

API documentation following OpenAPI 3.0.3 standard.
"""
from flask import Flask, jsonify
from acas_pro.core.config import config


API_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "ACAS Pro API",
        "description": "Automatic Customer Acquisition System - Production API",
        "version": config().version,
        "contact": {
            "name": "ACAS Pro Team"
        },
        "license": {
            "name": "Proprietary"
        }
    },
    "servers": [
        {
            "url": "/api",
            "description": "Current server"
        }
    ],
    "paths": {
        "/health": {
            "get": {
                "summary": "Health check",
                "description": "Comprehensive health check for monitoring and load balancers",
                "tags": ["System"],
                "responses": {
                    "200": {
                        "description": "System is healthy or degraded",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HealthResponse"
                                }
                            }
                        }
                    },
                    "503": {
                        "description": "System is unhealthy",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HealthResponse"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/auth/register": {
            "post": {
                "summary": "Register new user",
                "description": "Create a new user account with password validation",
                "tags": ["Authentication"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/RegisterRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Registration successful",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/AuthResponse"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid request",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    "409": {
                        "description": "Account already exists",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    "429": {
                        "description": "Rate limit exceeded"
                    }
                }
            }
        },
        "/auth/login": {
            "post": {
                "summary": "User login",
                "description": "Authenticate user and receive JWT token",
                "tags": ["Authentication"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/LoginRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Login successful",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/AuthResponse"
                                }
                            }
                        }
                    },
                    "401": {
                        "description": "Invalid credentials",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    "429": {
                        "description": "Rate limit exceeded"
                    }
                }
            }
        },
        "/auth/me": {
            "get": {
                "summary": "Get current user",
                "description": "Retrieve information about the authenticated user",
                "tags": ["Authentication"],
                "security": [{"bearerAuth": []}],
                "responses": {
                    "200": {
                        "description": "User information",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/UserInfo"
                                }
                            }
                        }
                    },
                    "401": {
                        "description": "Not authenticated"
                    }
                }
            }
        },
        "/llm/config": {
            "post": {
                "summary": "Configure LLM",
                "description": "Update LLM provider and API key configuration",
                "tags": ["LLM"],
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/LLMConfigRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Configuration saved"
                    },
                    "401": {
                        "description": "Not authenticated"
                    }
                }
            }
        },
        "/llm/chat": {
            "post": {
                "summary": "Chat with LLM",
                "description": "Send messages to configured LLM provider",
                "tags": ["LLM"],
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ChatRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Chat response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ChatResponse"
                                }
                            }
                        }
                    },
                    "401": {
                        "description": "Not authenticated"
                    },
                    "500": {
                        "description": "LLM service error"
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "HealthResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["healthy", "degraded", "unhealthy"]},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "version": {"type": "string"},
                    "environment": {"type": "string"},
                    "response_time_ms": {"type": "number"},
                    "checks": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                }
            },
            "RegisterRequest": {
                "type": "object",
                "required": ["account", "password"],
                "properties": {
                    "account": {"type": "string", "minLength": 3, "maxLength": 50},
                    "password": {"type": "string", "minLength": 8, "maxLength": 128},
                    "nickname": {"type": "string", "maxLength": 100}
                }
            },
            "LoginRequest": {
                "type": "object",
                "required": ["account", "password"],
                "properties": {
                    "account": {"type": "string"},
                    "password": {"type": "string"}
                }
            },
            "AuthResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "token": {"type": "string"},
                    "user": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "account": {"type": "string"},
                            "nickname": {"type": "string"}
                        }
                    }
                }
            },
            "UserInfo": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "account": {"type": "string"}
                }
            },
            "LLMConfigRequest": {
                "type": "object",
                "properties": {
                    "provider": {"type": "string", "enum": ["openai", "anthropic", "kimi", "deepseek", "qwen"]},
                    "api_key": {"type": "string"},
                    "api_base": {"type": "string"},
                    "model": {"type": "string"}
                }
            },
            "ChatRequest": {
                "type": "object",
                "required": ["messages"],
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                                "content": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "ChatResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "response": {"type": "string"},
                    "model": {"type": "string"},
                    "provider": {"type": "string"}
                }
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "message": {"type": "string"},
                    "request_id": {"type": "string"}
                }
            }
        },
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
    }
}


def register_api_docs(app: Flask):
    """Register API documentation endpoints"""
    
    @app.route('/api/openapi.json', methods=['GET'])
    def openapi_spec():
        """Return OpenAPI specification"""
        return jsonify(API_SPEC)
    
    @app.route('/api/docs', methods=['GET'])
    def api_docs():
        """Serve Swagger UI HTML"""
        html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ACAS Pro API Documentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({
            url: '/api/openapi.json',
            dom_id: '#swagger-ui',
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.presets.standalone
            ]
        });
    </script>
</body>
</html>'''
        return html
