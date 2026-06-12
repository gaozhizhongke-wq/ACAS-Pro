"""Coverage boost: cover the last ~4 lines to reach 80%."""


class TestPlatformApiFactoryCoverage:
    """Cover platform_api_factory.py line 58."""

    def test_get_supported_platforms(self):
        from acas_pro.ecommerce.platform_api_factory import get_supported_platforms
        result = get_supported_platforms()
        assert isinstance(result, list)


class TestMiddleware500Handler:
    """Cover middleware.py lines 108-109 (500 error handler)."""

    def test_internal_error_with_exception(self):
        from flask import Flask
        from acas_pro.web.middleware import ErrorHandler

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['PROPAGATE_EXCEPTIONS'] = False  # let error handlers run
        ErrorHandler.init_app(app)

        @app.route("/boom")
        def boom():
            raise RuntimeError("kaboom")

        with app.test_client() as client:
            resp = client.get("/boom")
            assert resp.status_code == 500
            data = resp.get_json()
            assert data["error"] == "Internal Server Error"


class TestAnalyticsTimeRangeEdge:
    """Cover analytics_logic.py else branch (line ~91)."""

    def test_time_range_custom_no_dates_fallback(self):
        from acas_pro.ui.logic.analytics_logic import AnalyticsLogic, TimeRange
        engine = AnalyticsLogic()
        # CUSTOM without custom_start/end → hits else branch → fallback to 7 days
        start, end = engine.get_time_range(TimeRange.CUSTOM)
        assert start is not None
        assert end is not None
