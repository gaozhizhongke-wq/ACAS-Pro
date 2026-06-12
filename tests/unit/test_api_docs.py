"""
Tests for API documentation endpoints (web/api_spec.py)
"""
import json
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app_with_docs():
    """Create a Flask app with API docs registered."""
    import sys
    sys.path.insert(0, 'src')
    
    from acas_pro.web import create_app
    app = create_app({'TESTING': True})
    return app


@pytest.fixture
def client(app_with_docs):
    """Test client for the app with API docs."""
    with app_with_docs.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# Tests for /api/openapi.json
# ---------------------------------------------------------------------------

class TestOpenAPIJson:
    """Tests for /api/openapi.json endpoint."""

    def test_endpoint_returns_200(self, client):
        resp = client.get('/api/openapi.json')
        assert resp.status_code == 200

    def test_endpoint_returns_json(self, client):
        resp = client.get('/api/openapi.json')
        assert resp.mimetype == 'application/json'
        data = json.loads(resp.data)
        assert data['openapi'] == '3.0.0'
        assert data['info']['title'] == 'ACAS Pro API'

    def test_spec_has_paths(self, client):
        resp = client.get('/api/openapi.json')
        data = json.loads(resp.data)
        assert '/auth/register' in data['paths']
        assert '/auth/login' in data['paths']
        assert '/metrics' in data['paths']

    def test_spec_has_security_schemes(self, client):
        resp = client.get('/api/openapi.json')
        data = json.loads(resp.data)
        assert 'securitySchemes' in data['components']
        assert 'bearerAuth' in data['components']['securitySchemes']


# ---------------------------------------------------------------------------
# Tests for /api/docs (Swagger UI)
# ---------------------------------------------------------------------------

class TestSwaggerUI:
    """Tests for /api/docs endpoint."""

    def test_endpoint_returns_200(self, client):
        resp = client.get('/api/docs')
        assert resp.status_code == 200

    def test_endpoint_returns_html(self, client):
        resp = client.get('/api/docs')
        assert 'text/html' in resp.mimetype
        assert b'html' in resp.data.lower()
        assert b'swagger' in resp.data.lower()


# ---------------------------------------------------------------------------
# Tests for api_spec module
# ---------------------------------------------------------------------------

class TestApiSpecModule:
    """Tests for the api_spec module itself."""

    def test_openapi_spec_is_valid(self):
        from acas_pro.web.api_spec import OPENAPI_SPEC
        assert OPENAPI_SPEC['openapi'] == '3.0.0'
        assert 'info' in OPENAPI_SPEC
        assert 'paths' in OPENAPI_SPEC
        assert 'components' in OPENAPI_SPEC

    def test_openapi_spec_has_tags(self):
        from acas_pro.web.api_spec import OPENAPI_SPEC
        tags = [tag['name'] for tag in OPENAPI_SPEC['tags']]
        assert 'auth' in tags
        assert 'dashboard' in tags
        assert 'llm' in tags
        assert 'metrics' in tags

    def test_register_api_docs_function_exists(self):
        from acas_pro.web.api_spec import register_api_docs
        assert callable(register_api_docs)

    def test_docs_blueprint_exists(self):
        from acas_pro.web.api_spec import docs_bp
        assert docs_bp.name == 'api_docs'
        assert docs_bp.url_prefix == '/api/docs'
