# powervaultpy

A Python client library for the Powervault battery API, used primarily by the [Home Assistant Powervault integration](https://github.com/adammcdonagh/home-assistant-powervault).

Supports both the **cloud REST API** (P4 & P5) and the **local API** available on legacy units (P3 & P3X).

---

## Installation

```bash
pip install powervaultpy
```

---

## Cloud API

The cloud API requires a paid API key obtained directly from Powervault. Based on the Swagger docs at [https://app.swaggerhub.com/apis-docs/Powervault/PowervaultP3/](https://app.swaggerhub.com/apis-docs/Powervault/PowervaultP3/).

### Usage

```python
from powervaultpy import PowerVault

client = PowerVault(api_key="your-api-key")

# Get account details
account = client.get_account()
# {"id": 123, "accountName": "..."}

# List units on the account
units = client.get_units(account["id"])

# Get details for a specific unit
unit = client.get_unit(units[0]["id"])

# Get latest telemetry data
data = client.get_data(unit["id"])

# Get telemetry for a specific period
data = client.get_data(unit["id"], period="past-hour")

# Get the current effective battery state (schedule + any active override)
state = client.get_battery_state(unit["id"])

# Override the battery state for the next 24 hours
client.set_battery_state(unit["id"], "force-charge")
```

### Available periods for `get_data`

`today`, `yesterday`, `past-hour`, `last-hour`, `past-day`, `last-day`, `past-week`, `last-week`, `past-month`, `last-month`

---

## Local API (legacy units)

Powervault legacy units expose a local HTTP API on port `5000`. No API key is required. Pass the unit's IP address to the constructor — the client will then use the local API automatically for all calls.

> `get_units`, `get_unit`, and `get_account` are cloud-only. Calling them on a local client will raise `PowerVaultApiClientError`.
>
> `get_health` and `get_unit_id` are local-only. Calling them on a cloud client will raise `PowerVaultApiClientError`.

### Usage

```python
from powervaultpy import PowerVault

client = PowerVault(local_ip="192.168.1.100")

UNIT_ID = "008a2564"

# Check device health
health = client.get_health()
# {"status": "ok"}

# Get the unit ID from the device itself
uid = client.get_unit_id()
# "008a2564"

# Get latest telemetry (list of measurement records)
data = client.get_data(UNIT_ID)

# Get the current effective battery state
state = client.get_battery_state(UNIT_ID)

# Override the battery state for the next 24 hours
client.set_battery_state(UNIT_ID, "force-charge")
```

### Local API endpoints

| Method | Local endpoint |
|---|---|
| `get_health` | `GET /api/health` | Local only |
| `get_unit_id` | `GET /api/unit-id` | Local only |
| `get_data` | `GET /api/latest-telemetry` | Both |
| `get_battery_state` | `GET /api/schedule` + `GET /api/state-override` | Both |
| `set_battery_state` | `POST /api/state-override` | Both |
| `get_units` | Cloud only | Cloud only |
| `get_unit` | Cloud only | Cloud only |
| `get_account` | Cloud only | Cloud only |

---

## Valid battery states

```python
from powervaultpy import VALID_STATUSES
```

| State | Description |
|---|---|
| `normal` | Follow the configured schedule |
| `only-charge` | Only charge (from grid or solar) |
| `only-discharge` | Only discharge |
| `force-charge` | Force charge from grid |
| `force-discharge` | Force discharge to grid/home |
| `disable` | Disable the battery |
| `dormant` | Dormant mode |

---

## Battery state override warning

> ⚠️ **WARNING:** Calling `set_battery_state` overrides any schedule configured in the Powervault portal for the next **24 hours**. Only use this if you are managing the battery state externally (e.g. via Home Assistant automations) and do not rely on the portal scheduler.

---

## Development

```bash
pip install -e ".[dev]"
```

### Running tests

**Unit tests** (no device or API key required — all mocked):

```bash
pytest tests/unit/
```

**Integration tests — cloud API** (requires `API_KEY` in `.env`):

```bash
pytest tests/integration/api/test_get_account.py
```

**Integration tests — local API** (requires `LOCAL_IP` and `UNIT_ID` in `.env`):

```bash
pytest tests/integration/api/test_local_api.py
```

### `.env` file

```env
API_KEY=your-cloud-api-key
LOCAL_IP=192.168.1.100
UNIT_ID=008a2564
```
