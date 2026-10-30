from django.db import models
 
class EventLog(models.Model):
    event_id = models.UUIDField(unique=True)
    source_id = models.CharField(max_length=120)
    event_type = models.CharField(max_length=32)
    event_time = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField()
 
class SystemState(models.Model):
    source_id = models.CharField(max_length=120, unique=True)
    last_heartbeat = models.DateTimeField(null=True)
    reported_status = models.CharField(max_length=32, default="unknown")
 
class MeasurementResult(models.Model):
    original_event_id = models.UUIDField(unique=True)
    device_id = models.CharField(max_length=120)
    value = models.FloatField()
    threshold = models.FloatField()
    status = models.CharField(max_length=16)
    is_anomaly = models.BooleanField(default=False)
    measured_at = models.DateTimeField()
    processed_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)
