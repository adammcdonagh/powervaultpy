"""Integration tests for the local (legacy) API.

These tests require a real Powervault device on the local network.
Set LOCAL_IP and UNIT_ID in your .env file to run them.
Tests are skipped automatically if those variables are not present.
"""

import logging
import os
from datetime import datetime, timedelta

import pytest
import pytz
from dotenv import load_dotenv

from powervaultpy import PowerVault, VALID_STATUSES

logging.basicConfig(level=logging.DEBUG)

DOTENV_FILE = os.path.join(os.path.dirname(__file__), "../../../.env")
if os.path.exists(DOTENV_FILE):
    load_dotenv(DOTENV_FILE)

LOCAL_IP = os.environ.get("LOCAL_IP")
UNIT_ID = os.environ.get("UNIT_ID_LOCAL")

pytestmark = pytest.mark.skipif(
    not LOCAL_IP or not UNIT_ID,
    reason="LOCAL_IP and UNIT_ID must be set in .env to run local API integration tests",
)


@pytest.fixture(scope="module")
def client():
    return PowerVault(local_ip=LOCAL_IP)


def test_get_health(client):
    result = client.get_health()

    assert result is not None
    assert "status" in result
    assert result["status"] == "ok"


def test_get_unit_id(client):
    result = client.get_unit_id()

    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_unit_id_matches_known_unit(client):
    result = client.get_unit_id()

    assert result == UNIT_ID


def test_get_data_local(client):
    result = client.get_data(UNIT_ID)

    assert result is not None
    assert isinstance(result, list)
    assert len(result) > 0

    # Each record should have expected fields
    measurements = {r["measurement"] for r in result}
    assert "actualState" in measurements
    assert "socAverage" in measurements or "socUsable" in measurements


def test_get_data_local_has_required_fields(client):
    result = client.get_data(UNIT_ID)

    for record in result:
        assert "measurement" in record
        assert "value" in record
        assert "unit" in record
        assert "timestamp" in record


def test_get_battery_state_local(client):
    result = client.get_battery_state(UNIT_ID)

    assert result is not None
    assert result in VALID_STATUSES


def test_set_battery_state_local_and_read_back(client):
    # Read the current state first
    original_state = client.get_battery_state(UNIT_ID)

    # Override to "only-charge"
    success = client.set_battery_state(UNIT_ID, "only-charge")
    assert success is True

    # Read back — should now reflect the override
    new_state = client.get_battery_state(UNIT_ID)
    assert new_state == "only-charge"

    # Now set it back and read back the original state
    success = client.set_battery_state(UNIT_ID, original_state)
    assert success is True
    new_state = client.get_battery_state(UNIT_ID)
    assert new_state == original_state


def test_get_chart_data(client):
    end = datetime.now(pytz.utc)
    start = end - timedelta(hours=24)

    result = client.get_chart_data(start, end)

    assert result is not None
    assert isinstance(result, list)
    assert len(result) > 0


def test_get_chart_data_records_have_timestamp(client):
    end = datetime.now(pytz.utc)
    start = end - timedelta(hours=1)

    result = client.get_chart_data(start, end)

    assert result is not None
    for record in result:
        for item in record:
            assert "timestamp" in item
