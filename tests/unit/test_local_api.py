"""Unit tests for the local (legacy) API support.

These tests use mocks and do NOT make real HTTP calls.
They verify URL construction, payload shapes, and response handling logic only.
For real-device verification, see tests/integration/api/test_local_api.py.
"""

import json
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import pytz
import requests
from dotenv import load_dotenv

from powervaultpy import PowerVault

DOTENV_FILE = os.path.join(os.path.dirname(__file__), "../../.env")
if os.path.exists(DOTENV_FILE):
    load_dotenv(DOTENV_FILE)

LOCAL_IP = os.environ.get("LOCAL_IP", "192.168.0.1")
UNIT_ID = os.environ.get("UNIT_ID", "testunit01")

# --- sample payloads matching real device responses ---

TELEMETRY_RESPONSE = [
    {
        "created_at": 1781180723.847219,
        "id": None,
        "measurement": "actualState",
        "timestamp": 1781180723.847219,
        "unit": "I|C",
        "value": "I",
    },
    {
        "created_at": 1781180723.847219,
        "id": None,
        "measurement": "batteryPower",
        "timestamp": 1781180723.847219,
        "unit": "watts",
        "value": -238,
    },
    {
        "created_at": 1781180723.847219,
        "id": None,
        "measurement": "gridPower",
        "timestamp": 1781180723.847219,
        "unit": "watts",
        "value": 55,
    },
    {
        "created_at": 1781180723.847219,
        "id": None,
        "measurement": "socAverage",
        "timestamp": 1781180723.847219,
        "unit": "percent",
        "value": 81,
    },
    {
        "created_at": 1781180723.847219,
        "id": None,
        "measurement": "socUsable",
        "timestamp": 1781180723.847219,
        "unit": "percent",
        "value": 80,
    },
    {
        "created_at": 1781180723.847219,
        "id": None,
        "measurement": "temperature",
        "timestamp": 1781180723.847219,
        "unit": "celsius",
        "value": 26.0,
    },
]

HEALTH_RESPONSE = {"status": "ok"}

UNIT_ID_RESPONSE = {"uid": "008a2564"}

SCHEDULE_RESPONSE = {
    "monday": [
        {"end": "05:29:59", "start": "00:00:00", "state": "force-charge"},
        {"end": "16:29:59", "start": "05:30:00", "state": "normal"},
        {"end": "23:29:59", "start": "16:30:00", "state": "normal"},
        {"end": "23:59:59", "start": "23:30:00", "state": "force-charge"},
    ],
    "tuesday": [
        {"end": "05:29:59", "start": "00:00:00", "state": "force-charge"},
        {"end": "23:59:59", "start": "05:30:00", "state": "normal"},
    ],
    "wednesday": [{"end": "23:59:59", "start": "00:00:00", "state": "normal"}],
    "thursday": [{"end": "23:59:59", "start": "00:00:00", "state": "normal"}],
    "friday": [{"end": "23:59:59", "start": "00:00:00", "state": "normal"}],
    "saturday": [{"end": "23:59:59", "start": "00:00:00", "state": "normal"}],
    "sunday": [{"end": "23:59:59", "start": "00:00:00", "state": "normal"}],
}

STATE_OVERRIDE_RESPONSE = {
    "end": "2026-06-12 12:15:28",
    "start": "2026-06-11 12:15:28",
    "state": "normal",
}

STATE_OVERRIDE_POST_RESPONSE = {"message": "State override saved", "status": "ok"}


def _make_response(payload, status_code=200):
    """Build a mock requests.Response for the given payload."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = status_code
    mock_resp.text = json.dumps(payload)
    return mock_resp


@pytest.fixture
def cloud_client():
    return PowerVault(api_key="test-key")


@pytest.fixture
def local_client():
    return PowerVault(local_ip=LOCAL_IP)


# ---------------------------------------------------------------------------
# _local_url
# ---------------------------------------------------------------------------


class TestLocalUrl:
    def test_builds_correct_url(self, local_client):
        assert local_client._local_url("health") == f"http://{LOCAL_IP}:5000/api/health"

    def test_builds_correct_url_with_hyphen(self, local_client):
        assert (
            local_client._local_url("latest-telemetry")
            == f"http://{LOCAL_IP}:5000/api/latest-telemetry"
        )


# ---------------------------------------------------------------------------
# constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    def test_raises_with_neither_arg(self):
        with pytest.raises(ValueError, match="Either api_key or local_ip"):
            PowerVault()

    def test_raises_with_both_args(self):
        with pytest.raises(ValueError, match="Only one of"):
            PowerVault(api_key="key", local_ip=LOCAL_IP)

    def test_cloud_client_has_no_local_ip(self, cloud_client):
        assert cloud_client._local_ip is None

    def test_local_client_has_no_api_key(self, local_client):
        assert local_client._api_key is None


# ---------------------------------------------------------------------------
# get_health
# ---------------------------------------------------------------------------


class TestGetHealth:
    def test_returns_health_response(self, local_client):
        local_client._session.get = MagicMock(
            return_value=_make_response(HEALTH_RESPONSE)
        )

        result = local_client.get_health()

        local_client._session.get.assert_called_once_with(
            f"http://{LOCAL_IP}:5000/api/health"
        )
        assert result == {"status": "ok"}

    def test_raises_on_server_error(self, local_client):
        from powervaultpy.powervault import ServerError

        local_client._session.get = MagicMock(
            return_value=_make_response({}, status_code=500)
        )

        with pytest.raises(ServerError):
            local_client.get_health()

    def test_raises_when_called_on_cloud_client(self, cloud_client):
        from powervaultpy.powervault import PowerVaultApiClientError

        with pytest.raises(PowerVaultApiClientError):
            cloud_client.get_health()


# ---------------------------------------------------------------------------
# get_unit_id
# ---------------------------------------------------------------------------


class TestGetUnitId:
    def test_returns_uid_string(self, local_client):
        local_client._session.get = MagicMock(
            return_value=_make_response(UNIT_ID_RESPONSE)
        )

        result = local_client.get_unit_id()

        local_client._session.get.assert_called_once_with(
            f"http://{LOCAL_IP}:5000/api/unit-id"
        )
        assert result == "008a2564"

    def test_returns_none_when_uid_missing(self, local_client):
        local_client._session.get = MagicMock(return_value=_make_response({}))

        result = local_client.get_unit_id()

        assert result is None

    def test_raises_when_called_on_cloud_client(self, cloud_client):
        from powervaultpy.powervault import PowerVaultApiClientError

        with pytest.raises(PowerVaultApiClientError):
            cloud_client.get_unit_id()


# ---------------------------------------------------------------------------
# get_data
# ---------------------------------------------------------------------------


class TestGetDataLocal:
    def test_returns_telemetry_list(self, local_client):
        local_client._session.get = MagicMock(
            return_value=_make_response(TELEMETRY_RESPONSE)
        )

        result = local_client.get_data(UNIT_ID)

        local_client._session.get.assert_called_once_with(
            f"http://{LOCAL_IP}:5000/api/latest-telemetry"
        )
        assert result == TELEMETRY_RESPONSE
        assert isinstance(result, list)

    def test_raises_on_server_error(self, local_client):
        from powervaultpy.powervault import ServerError

        local_client._session.get = MagicMock(
            return_value=_make_response({}, status_code=500)
        )

        with pytest.raises(ServerError):
            local_client.get_data(UNIT_ID)

    def test_cloud_uses_cloud_url_and_unwraps_data(self, cloud_client):
        cloud_payload = {"data": TELEMETRY_RESPONSE}
        cloud_client._session.get = MagicMock(
            return_value=_make_response(cloud_payload)
        )

        result = cloud_client.get_data(UNIT_ID)

        cloud_client._session.get.assert_called_once_with(
            f"https://rest-api.powervault.co.uk/v4/unit/{UNIT_ID}/data"
        )
        assert result == TELEMETRY_RESPONSE

    def test_cloud_period_appended_to_url(self, cloud_client):
        cloud_payload = {"data": TELEMETRY_RESPONSE}
        cloud_client._session.get = MagicMock(
            return_value=_make_response(cloud_payload)
        )

        cloud_client.get_data(UNIT_ID, period="past-hour")

        cloud_client._session.get.assert_called_once_with(
            f"https://rest-api.powervault.co.uk/v4/unit/{UNIT_ID}/data?period=past-hour"
        )

    def test_invalid_period_raises_on_cloud_client(self, cloud_client):
        with pytest.raises(Exception, match="Invalid period"):
            cloud_client.get_data(UNIT_ID, period="invalid-period")


# ---------------------------------------------------------------------------
# set_battery_state
# ---------------------------------------------------------------------------


class TestSetBatteryStateLocal:
    def test_returns_true_on_success(self, local_client):
        local_client._session.post = MagicMock(
            return_value=_make_response(STATE_OVERRIDE_POST_RESPONSE)
        )

        result = local_client.set_battery_state(UNIT_ID, "force-charge")

        local_client._session.post.assert_called_once()
        url_called = local_client._session.post.call_args[0][0]
        assert url_called == f"http://{LOCAL_IP}:5000/api/state-override"
        assert result is True

    def test_post_payload_shape(self, local_client):
        local_client._session.post = MagicMock(
            return_value=_make_response(STATE_OVERRIDE_POST_RESPONSE)
        )

        local_client.set_battery_state(UNIT_ID, "normal")

        _, kwargs = local_client._session.post.call_args
        payload = kwargs["json"]
        assert "start" in payload
        assert "end" in payload
        assert payload["state"] == "normal"
        # Local payload is a flat object, not wrapped in stateOverrides list
        assert "stateOverrides" not in payload

    def test_returns_false_on_non_ok_status(self, local_client):
        local_client._session.post = MagicMock(
            return_value=_make_response({"message": "error", "status": "fail"})
        )

        result = local_client.set_battery_state(UNIT_ID, "normal")

        assert result is False

    def test_cloud_uses_cloud_url_and_payload_shape(self, cloud_client):
        cloud_resp = {"stateOverrides": [{}], "message": "success"}
        cloud_client._session.post = MagicMock(return_value=_make_response(cloud_resp))

        result = cloud_client.set_battery_state(UNIT_ID, "normal")

        url_called = cloud_client._session.post.call_args[0][0]
        assert (
            url_called
            == f"https://rest-api.powervault.co.uk/v4/unit/{UNIT_ID}/stateOverride"
        )
        assert result is True


# ---------------------------------------------------------------------------
# get_battery_state
# ---------------------------------------------------------------------------


class TestGetBatteryStateLocal:
    def _make_side_effect(self, schedule_payload, override_payload):
        """Return a side_effect function that returns appropriate responses per URL."""

        def side_effect(url):
            if "schedule" in url:
                return _make_response(schedule_payload)
            if "state-override" in url:
                return _make_response(override_payload)
            return _make_response({})

        return side_effect

    def test_returns_schedule_state_when_no_active_override(self, local_client):
        # Override in the past — should not apply
        past_override = {
            "start": "2020-01-01 00:00:00",
            "end": "2020-01-02 00:00:00",
            "state": "force-discharge",
        }
        local_client._session.get = MagicMock(
            side_effect=self._make_side_effect(SCHEDULE_RESPONSE, past_override)
        )

        # Patch datetime to control current time — pin to a Wednesday at 12:00 (normal slot)
        fixed_dt = datetime(
            2026, 6, 10, 12, 0, 0, tzinfo=pytz.timezone("Europe/London")
        )
        with patch("powervaultpy.powervault.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_dt
            mock_dt.strptime.side_effect = datetime.strptime

            result = local_client.get_battery_state(UNIT_ID)

        assert result == "normal"

    def test_active_override_takes_precedence(self, local_client):
        # Override that spans the current moment
        now_utc = datetime.now(pytz.utc)
        active_override = {
            "start": (now_utc - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "end": (now_utc + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "state": "force-charge",
        }
        local_client._session.get = MagicMock(
            side_effect=self._make_side_effect(SCHEDULE_RESPONSE, active_override)
        )

        result = local_client.get_battery_state(UNIT_ID)

        assert result == "force-charge"

    def test_calls_correct_local_endpoints(self, local_client):
        now_utc = datetime.now(pytz.utc)
        active_override = {
            "start": (now_utc - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "end": (now_utc + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "state": "normal",
        }
        local_client._session.get = MagicMock(
            side_effect=self._make_side_effect(SCHEDULE_RESPONSE, active_override)
        )

        local_client.get_battery_state(UNIT_ID)

        urls = [c[0][0] for c in local_client._session.get.call_args_list]
        assert f"http://{LOCAL_IP}:5000/api/schedule" in urls
        assert f"http://{LOCAL_IP}:5000/api/state-override" in urls

    def test_raises_when_no_matching_schedule_slot(self, local_client):
        # Empty schedule for all days
        empty_schedule = {
            day: []
            for day in [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]
        }
        past_override = {
            "start": "2020-01-01 00:00:00",
            "end": "2020-01-02 00:00:00",
            "state": "normal",
        }
        local_client._session.get = MagicMock(
            side_effect=self._make_side_effect(empty_schedule, past_override)
        )

        with pytest.raises(Exception, match="Failed to determine current state"):
            local_client.get_battery_state(UNIT_ID)

    def test_cloud_uses_cloud_urls(self, cloud_client):
        cloud_schedule = {"schedule": SCHEDULE_RESPONSE}
        now_utc = datetime.now(pytz.utc)
        cloud_override = {
            "stateOverrides": [
                {
                    "start": (now_utc - timedelta(hours=1)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "end": (now_utc + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                    "state": "only-discharge",
                }
            ]
        }

        def cloud_side_effect(url):
            if "schedule" in url:
                return _make_response(cloud_schedule)
            if "stateOverride" in url:
                return _make_response(cloud_override)
            return _make_response({})

        cloud_client._session.get = MagicMock(side_effect=cloud_side_effect)

        result = cloud_client.get_battery_state(UNIT_ID)

        urls = [c[0][0] for c in cloud_client._session.get.call_args_list]
        assert any("rest-api.powervault.co.uk" in u for u in urls)
        assert result == "only-discharge"
