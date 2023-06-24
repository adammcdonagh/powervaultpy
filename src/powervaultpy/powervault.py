"""Sample API Client."""

import json
import logging
from datetime import datetime, timedelta

import pytz
import requests

VALID_STATUSES = [
    "normal",
    "only-charge",
    "only-discharge",
    "force-charge",
    "force-discharge",
    "disable",
    "dormant",
]

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

class PowerVaultApiClientError(Exception):
    """Exception to indicate a general API error."""


class PowerVaultApiClientCommunicationError(PowerVaultApiClientError):
    """Exception to indicate a communication error."""


class PowerVaultApiClientAuthenticationError(PowerVaultApiClientError):
    """Exception to indicate an authentication error."""


class ServerError(Exception):
    ...


class RequestError(Exception):
    ...


class PowerVault:
    """API Client."""

    def __init__(
        self,
        api_key: str,
        session: requests.Session = None,
    ) -> None:
        """API Client."""
        self._api_key = api_key
        self._base_url = "https://api.p3.powervault.co.uk/v3"
        self._session = session or requests.Session()

        self._session.headers.update(
            {
                "x-api-key": self._api_key,
                "accept": "application/json",
            }
        )

    def get_units(self, account_id: int) -> any:
        """Get the user's units from the API."""
        url = f"{self._base_url}/unit?customerAccountId={account_id}"
        units_response = self._read_response(self._session.get(url), url)

        _LOGGER.debug("Units: %s", units_response)

        if (
            units_response is not None
            and "units" in units_response
            and units_response["units"] is not None
        ):
            return units_response["units"]

        _LOGGER.error("Failed to retrieve units")

    def get_unit(self, unit_id: int) -> any:
        """Get the unit details from the API."""
        url = f"{self._base_url}/unit/{unit_id}"
        unit_response = self._read_response(self._session.get(url), url)

        _LOGGER.debug("Unit: %s", unit_response)

        if (
            unit_response is not None
            and "unit" in unit_response
        ):
            return unit_response["unit"]

        _LOGGER.error("Failed to retrieve unit")

    def get_account(self) -> any:
        """Get the user's account data from the API."""
        url = f"{self._base_url}/customerAccount"

        account_response = self._read_response(self._session.get(url), url)

        _LOGGER.debug("Account: %s", account_response)

        if (
            account_response is not None
            and "customerAccount" in account_response
            and "id" in account_response["customerAccount"]
            and account_response["customerAccount"]["id"] is not None
        ):
            return {
                "id": account_response["customerAccount"]["id"],
                "accountName": account_response["customerAccount"]["accountName"],
            }

        _LOGGER.error("Failed to retrieve account")

    def get_data(
        self, unit_id: str, from_: int = -1, to: int = -1, period: str = None
    ) -> any:
        """Get the latest metrics from the unit."""
        url = f"{self._base_url}/unit/{unit_id}/data"

        if from_ > 0 and to > 0:
            url = f"{url}?from={from_}&to={to}"
        elif period is not None:
            if period not in [
                "today",
                "yesterday",
                "past-hour",
                "last-hour",
                "past-day",
                "last-day",
                "past-week",
                "last-week",
                "past-month",
                "last-month",
            ]:
                raise Exception(f"Invalid period: {period}")
            url = f"{url}?period={period}"

        data_response = self._read_response(self._session.get(url), url)
        _LOGGER.debug("Data: %s", data_response)

        if (data_response is not None) and ("data" in data_response):
            return data_response["data"]

        _LOGGER.error("Failed to retrieve data")

    def get_kwh(self, data: dict) -> dict:
        # List of attributes to retrieve from data dict
        attributes = [
            "batteryInputFromGrid",
            "batteryInputFromSolar",
            "batteryOutputConsumedByHome",
            "batteryOutputExported",
            "homeConsumed",
            "gridConsumedByHome",
            "solarConsumedByHome",
            "solarExported",
            "solarGenerated",
        ]
        # For each attribute, loop through the data dict and conver the W reading to kWh over the 5 minute period
        totals = {}
        for row in data:
            for attribute in attributes:
                if attribute in row:
                    if attribute not in totals:
                        totals[attribute] = 0
                    totals[attribute] += round(row[attribute] / 1000 * (5/60), 2)

        return totals

    def set_battery_state(self, unit_id: str, battery_state) -> bool:
        """Override the current battery status with the provided one."""
        url = f"{self._base_url}/unit/{unit_id}/stateOverride"

        start_time = datetime.now(pytz.timezone('UTC')).strftime("%Y-%m-%d %H:%M:%S")
        end_time = (datetime.now(pytz.timezone('UTC')) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

        payload = {
            "stateOverrides": [
                {
                    "start": start_time,
                    "end": end_time,
                    "state": battery_state
                }
            ]
        }

        _LOGGER.debug("Payload: %s", payload)

        state_override_response = self._read_response(
            self._session.post(url, json=payload), url)
        
        _LOGGER.debug("State Override: %s", state_override_response)

        if (state_override_response is not None) and ("stateOverrides" in state_override_response) and "message" in state_override_response and state_override_response["message"] == "success":
            return True
        else:
            return False
        

    def get_battery_state(self, unit_id: str) -> any:
        """Query the schedule and overrides to determine the current battery state."""
        url = f"{self._base_url}/unit/{unit_id}/schedule"

        schedule_response = self._read_response(self._session.get(url), url)
        _LOGGER.debug("Schedule: %s", schedule_response)

        url = f"{self._base_url}/unit/{unit_id}/stateOverride"

        state_override_response = self._read_response(self._session.get(url), url)
        _LOGGER.debug("State Override: %s", state_override_response)

        # Get the current local datetime
        current_dow = datetime.now(pytz.timezone("Europe/London")).strftime("%A").lower()

        # Log the current day of the week
        _LOGGER.debug("Current day of the week: %s", current_dow)

        # Get the current time
        current_time = datetime.now(pytz.timezone('Europe/London'))

        current_state = None
        # Loop through the schedule to find the current state
        # These values are in LOCALTIME
        for schedule_dow in schedule_response["schedule"]:
            schedule = schedule_response["schedule"][schedule_dow]
            if schedule_dow.lower() == current_dow:
                for days_events in schedule:
                    _LOGGER.debug("Schedule: %s", days_events)
                    start_time = datetime.strptime(
                        days_events["start"], "%H:%M:%S"
                    ).time()
                    end_time = datetime.strptime(days_events["end"], "%H:%M:%S").time()

                    if current_time.time() >= start_time and current_time.time() <= end_time:
                        _LOGGER.debug("Current state: %s", days_events["state"])
                        current_state = days_events["state"]
                        break

        # If there is a state override, use that instead
        # These values are in UTC!
        if state_override_response is not None and "stateOverrides" in state_override_response:
            for state_override in state_override_response["stateOverrides"]:
                # Check the start and end times
                start_time = datetime.strptime(state_override["start"], "%Y-%m-%d %H:%M:%S")
                start_time = pytz.utc.localize(start_time)
                end_time = datetime.strptime(state_override["end"], "%Y-%m-%d %H:%M:%S")
                end_time = pytz.utc.localize(end_time)

                # Convert to local time
                start_time = start_time.astimezone()
                end_time = end_time.astimezone()

                if current_time >= start_time and current_time <= end_time:
                    _LOGGER.debug("Current state: %s", state_override["state"])
                    current_state = state_override["state"]
                    break

        if current_state is None:
            raise Exception("Failed to determine current state")

        return current_state


    def _read_response(self, response: requests.Response, url):
        """Reads the response, logging any json errors"""

        text = response.text

        if response.status_code >= 400:
            if response.status_code >= 500:
                msg = (
                    f"DO NOT REPORT - PowerVault server error ({url}):"
                    f" {response.status_code}; {text}"
                )
                _LOGGER.debug(msg)
                raise ServerError(msg)
            if response.status_code not in [401, 403, 404]:
                msg = f"Failed to send request ({url}): {response.status_code}; {text}"
                _LOGGER.debug(msg)
                raise RequestError(msg)
            return None

        try:
            return json.loads(text)
        except:
            raise Exception(f"Failed to extract response json: {url}; {text}")
