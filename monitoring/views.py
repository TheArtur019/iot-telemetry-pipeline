from datetime import timedelta
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET
from .models import EventLog, MeasurementResult, SystemState
 
@require_GET
def index(request):
    return render(request, "monitoring/index.html")
 
@require_GET
def state(request):
    now = timezone.now()
    systems = []
    for item in SystemState.objects.order_by("source_id"):
        age = ((now - item.last_heartbeat).total_seconds()
               if item.last_heartbeat else None)
        if age is None:
            freshness = "нет данных"
        elif age < -5:
            freshness = "ошибка часов"
        elif age <= 10:
            freshness = "актуально"
        elif age <= 30:
            freshness = "задержка"
        else:
            freshness = "нет свежих данных"
        systems.append({
            "source": item.source_id, "freshness": freshness,
            "age": round(age, 1) if age is not None else None,
            "reported_status": item.reported_status,
        })
    recent = MeasurementResult.objects.filter(
        measured_at__gte=now - timedelta(minutes=5),
        measured_at__lte=now,
    )
    total = recent.count()
    warnings = recent.filter(status="warning").count()
    latest = EventLog.objects.order_by("-received_at").first()
    return JsonResponse({
        "server_time": now,
        "last_ingested_at": latest.received_at if latest else None,
        "systems": systems,
        "total_5m": total, "warnings_5m": warnings,
        "warning_share": warnings / total if total else None,
        "results": list(MeasurementResult.objects.order_by(
            "-measured_at").values(
                "device_id", "value", "status", "measured_at")[:30]),
        "invalid": list(EventLog.objects.filter(
            event_type="invalid").order_by("-received_at").values(
                "received_at", "payload")[:10]),
    })
