"""V2 Web Routes Tests"""
import pytest


class TestWebRoutesV2:
    @pytest.mark.skip(reason="V1 import conflict")
    def test_auth_blueprint(self):
        pass


class TestHealthV2:
    @pytest.mark.skip(reason="V1 import conflict")
    def test_health_check(self):
        pass
