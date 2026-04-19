"""Tests for orca_cli.core.exceptions — error hierarchy + formatting."""

from __future__ import annotations

from orca_cli.core.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    OrcaCLIError,
)


class TestAPIError:

    def test_known_status_uses_friendly_label(self):
        err = APIError(404, "resource gone")
        assert "Not found" in str(err) or "Not found" in err.message
        assert err.status_code == 404

    def test_unknown_status_falls_back(self):
        err = APIError(418, "teapot")
        assert "HTTP 418" in err.message

    def test_no_detail_omits_colon(self):
        err = APIError(503)
        assert "Service unavailable" in err.message
        assert err.message.endswith("(503)")

    def test_detail_appended(self):
        err = APIError(400, "bad field 'foo'")
        assert "bad field 'foo'" in err.message


class TestAuthenticationError:

    def test_default_message_suggests_setup(self):
        err = AuthenticationError()
        assert "orca setup" in err.message

    def test_custom_message(self):
        err = AuthenticationError("token expired")
        assert err.message == "token expired"


class TestConfigurationError:

    def test_default_message_suggests_setup(self):
        err = ConfigurationError()
        assert "orca setup" in err.message

    def test_custom_message(self):
        err = ConfigurationError("missing auth_url")
        assert err.message == "missing auth_url"


class TestHierarchy:

    def test_all_subclass_orca_cli_error(self):
        assert issubclass(APIError, OrcaCLIError)
        assert issubclass(AuthenticationError, OrcaCLIError)
        assert issubclass(ConfigurationError, OrcaCLIError)
