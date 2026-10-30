from datetime import datetime
from django.db import transaction
from django.utils import timezone
from .models import EventLog, MeasurementResult, SystemState
 
def parse_time(value):
    result = datetime.fromisoformat(value)
    if timezone.is_naive(result):
        raise ValueError("Timezone is required")
    return result
 
@transaction.atomic
def save_event(item):
    timestamp = parse_time(item["event_time"])
    payload = item["payload"]
    record, created = EventLog.objects.get_or_create(
        event_id=item["event_id"], defaults={
            "source_id": item["source_id"],
            "event_type": item["event_type"],
            "event_time": timestamp, "payload": payload,
        })
    if not created:
        return False
    if item["event_type"] == "heartbeat":
        state, _ = SystemState.objects.get_or_create(
            source_id=item["source_id"])
        state = SystemState.objects.select_for_update().get(pk=state.pk)
        if state.last_heartbeat is None or timestamp > state.last_heartbeat:
            state.last_heartbeat = timestamp
            state.reported_status = payload["status"]
            state.save()
    elif item["event_type"] == "result":
        MeasurementResult.objects.get_or_create(
            original_event_id=payload["original_event_id"], defaults={
                "device_id": payload["device_id"],
                "value": payload["value"],
                "threshold": payload["threshold"],
                "status": payload["status"],
                "is_anomaly": payload["is_anomaly"],
                "measured_at": parse_time(payload["measured_at"]),
                "processed_at": timestamp,
            })
    return True
