import json
import math
import uuid
from datetime import datetime
 
 
def parse_measurement(raw):
    """Validate the raw topic contract before publishing a result."""
    try:
        item = json.loads(raw)
        if not isinstance(item, dict):
            raise ValueError("Expected a JSON object")
        if type(item["schema_version"]) is not int:
            raise ValueError("schema_version must be an integer")
        if item["schema_version"] != 1:
            raise ValueError("Unsupported schema")
        if item["event_type"] != "measurement":
            raise ValueError("Expected measurement")
        if not isinstance(item["event_id"], str):
            raise ValueError("Expected UUID string")
        item["event_id"] = str(uuid.UUID(item["event_id"]))
        timestamp = datetime.fromisoformat(item["event_time"])
        if timestamp.utcoffset() is None:
            raise ValueError("event_time must include timezone")
        payload = item["payload"]
        value = payload["value"]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Expected a finite number")
        device = payload["device_id"]
        if not isinstance(device, str) or not 1 <= len(device) <= 120:
            raise ValueError("device_id length must be 1..120")
        if "\x00" in device:
            raise ValueError("device_id contains NUL")
        if payload["unit"] != "C":
            raise ValueError("Expected Celsius unit C")
        if type(payload["is_anomaly"]) is not bool:
            raise ValueError("is_anomaly must be a boolean")
        return item
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        raise ValueError(str(error)) from error
