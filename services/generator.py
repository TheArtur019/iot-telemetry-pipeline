import logging
import math
import os
import random
import threading
from services.common import event, producer, send, start_heartbeat
 
source = os.getenv("SOURCE_ID", "generator-1")
interval = float(os.getenv("SEND_INTERVAL", "1"))
probability = float(os.getenv("ANOMALY_PROBABILITY", "0.15"))
if not math.isfinite(interval) or interval <= 0 or not 0 <= probability <= 1:
    raise ValueError("Invalid generator parameters")
stop = threading.Event()
client = producer()
start_heartbeat(source, stop)
try:
    while True:
        device = random.choice(["motor-1", "motor-2", "motor-3"])
        anomaly = random.random() < probability
        value = random.gauss(95 if anomaly else 60, 4)
        item = event(source, "measurement", {
            "device_id": device,
            "value": round(value, 2),
            "unit": "C",
            "is_anomaly": anomaly,
        })
        send(client, "telemetry.raw", device, item)
        logging.info("Sent %s %s", device, item["event_id"])
        stop.wait(interval)
except KeyboardInterrupt:
    pass
finally:
    stop.set()
