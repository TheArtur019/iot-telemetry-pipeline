import logging
import math
import os
import socket
import threading
import time
import uuid
from services.common import (
    consumer, event, producer, send, start_heartbeat,
)
 
from services.validation import parse_measurement
 
 
def handle_message(msg, reader, writer, source, delay, threshold):
    coordinates = f"{msg.topic()}:{msg.partition()}:{msg.offset()}"
    try:
        item = parse_measurement(msg.value())
        payload = item["payload"]
        value = payload["value"]
        device = payload["device_id"]
    except ValueError as error:
        identifier = str(uuid.uuid5(uuid.NAMESPACE_URL,
                                   "invalid:" + coordinates))
        rejected = event(source, "invalid", {
            "error": str(error), "coordinates": coordinates,
            "raw": repr(msg.value()),
        }, identifier)
        send(writer, "telemetry.invalid", coordinates, rejected)
    else:
        time.sleep(delay)
        identifier = str(uuid.uuid5(uuid.NAMESPACE_URL,
                                   "rule-v1:" + item["event_id"]))
        result = event(source, "result", {
            "original_event_id": item["event_id"],
            "device_id": device, "value": value,
            "threshold": threshold,
            "status": "warning" if value > threshold else "normal",
            "measured_at": item["event_time"],
            "is_anomaly": payload.get("is_anomaly", False),
        }, identifier)
        send(writer, "telemetry.processed", device, result)
    reader.commit(message=msg, asynchronous=False)
    logging.info("Committed %s", coordinates)
 
 
def main():
    source = "processor-" + socket.gethostname()
    delay = float(os.getenv("PROCESSING_DELAY", "0.1"))
    threshold = float(os.getenv("TEMPERATURE_THRESHOLD", "80"))
    if not 0 <= delay <= 60 or not math.isfinite(threshold):
        raise ValueError("Invalid processor parameters")
    stop = threading.Event()
    start_heartbeat(source, stop)
    reader = consumer("processor-v1", ["telemetry.raw"])
    writer = producer()
    try:
        while True:
            msg = reader.poll(1)
            if msg is None:
                continue
            if msg.error():
                raise RuntimeError(msg.error())
            handle_message(msg, reader, writer, source, delay, threshold)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        reader.close()
 
 
if __name__ == "__main__":
    main()
