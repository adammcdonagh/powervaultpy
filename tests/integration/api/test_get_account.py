import logging
import re
import time

import pytest
from integration import get_test_context

from powervaultpy import PowerVault
import os
logging.basicConfig(level=logging.DEBUG)
os.environ["API_KEY"] = "1cxUBGXEJS2cY2uUrc3ji1X91r6j7rg79qYsj28R"

def test_get_account():
    # Arrange
    context = get_test_context()

    client = PowerVault(context["api_key"])

    # Act
    account = client.get_account()

    # Assert
    assert account is not None
    assert "id" in account

    assert re.match("^\\d+$", str(account["id"]))


def test_get_units():
    # Arrange
    context = get_test_context()

    client = PowerVault(context["api_key"])

    # Act
    account = client.get_account()
    units = client.get_units(account["id"])
    assert units is not None
    assert units != []
    assert units[0] is not None
    assert "id" in units[0]
    assert units[0]["id"] is not None
    assert re.match("^[^-]+-\\d+$", str(units[0]["id"]))

    print(units)

def test_get_data():
    # Arrange
    context = get_test_context()

    client = PowerVault(context["api_key"])

    # Act
    account = client.get_account()
    units = client.get_units(account["id"])

    data = client.get_data(units[0]["id"])

    assert data is not None
    assert data != []
    # Assert data contains only 1 row
    assert len(data) == 1

    # Query the past hour
    data = client.get_data(units[0]["id"], period="past-hour")
    assert data is not None
    assert data != []
    # Assert data contains 13 rows
    assert len(data) == 13

    # DISABLED FOR NOW AS THE API NO LONGER FUNCTIONS
    # # Query the past 30 minutes using epoch values (millsecond values)
    # now = int(round(time.time() * 1000))
    # data = client.get_data(units[0]["id"], from_=now - 1800000, to=now)
    # assert data is not None
    # assert data != []
    # # Assert data contains 7 rows
    # assert len(data) == 7

def test_get_totals_latest():
    context = get_test_context()

    client = PowerVault(context["api_key"])

    # Act
    account = client.get_account()
    units = client.get_units(account["id"])

    totals = client.get_data(units[0]["id"], period="today")

    # Check for None values in any of the total data. Use instant_battery as a test
    for row in totals:
        # Remove anything that is None
        if "instant_battery" not in row or row["instant_battery"] is None:
            totals.remove(row)

    totals = client.get_kwh(totals)
    print (totals)
    assert totals


def test_get_totals():
    context = get_test_context()

    client = PowerVault(context["api_key"])

    # Act
    account = client.get_account()
    units = client.get_units(account["id"])

    data = client.get_data(units[0]["id"], period="past-hour")

    totals = client.get_kwh(data)
    print(totals)

    # homeConsumed is good
    # solarGenerated is good
    # solarExported is good
    # batteryInputFromGrid is good
    # gridConsumedByHome is good

    # Solar consumed = solarConsumedByHome + batteryInputFromSolar
    # Home consumed = homeConsumed


def test_get_battery_state():
    context = get_test_context()

    client = PowerVault(context["api_key"])

    # Act
    account = client.get_account()
    units = client.get_units(account["id"])

    battery_state = client.get_battery_state(units[0]["id"])
    print(battery_state)


def test_set_battery_state():
    context = get_test_context()

    client = PowerVault(context["api_key"])

    # Act
    account = client.get_account()
    units = client.get_units(account["id"])

    battery_state = client.get_battery_state(units[0]["id"])
    print(battery_state)

    assert battery_state is not None

    # Set the battery state to "only-charge"
    client.set_battery_state(units[0]["id"], "only-charge")

    # Get the battery state again
    battery_state = client.get_battery_state(units[0]["id"])
    print(battery_state)

    assert battery_state == "only-charge"

@pytest.mark.asyncio
async def test_when_get_account_is_called_with_invalid_api_key():
    # Arrange
    context = get_test_context()

    client = PowerVault("invalid-key")

    # Act
    client.get_account()
