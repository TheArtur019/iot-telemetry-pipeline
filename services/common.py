import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from confluent_kafka import Consumer, Producer
 
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
BROKER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
 
def now():
    return datetime.now(timezone.utc).isoformat()
 
def event(source, kind, payload, event_id=None):
    return {
        "event_id": event_id or str(uuid.uuid4()),
        "source_id": source,
        "event_type": kind,
        "event_time": now(),
        "schema_version": 1,
        "payload": payload,
    }
 
def producer():
    return Producer({
        "bootstrap.servers": BROKER,
        "enable.idempotence": True,
        "acks": "all",
        "delivery.timeout.ms": 15000,
    })
 
def send(client, topic, key, data):
    # Synchronous delivery for a small teaching workload.
    result = []
    def delivered(error, message):
        result.append(error)
    client.produce(topic, key=key,
                   value=json.dumps(data).encode("utf-8"),
                   on_delivery=delivered)
    pending = client.flush(20)
    if pending or not result or result[0] is not None:
        raise RuntimeError(f"Delivery failed: {result}")
 
def consumer(group, topics):
    client = Consumer({
        "bootstrap.servers": BROKER,
        "group.id": group,
        "enable.auto.commit": False,
        "enable.auto.offset.store": False,
        "auto.offset.reset": "earliest",
        "max.poll.interval.ms": 300000,
    })
    client.subscribe(topics)
    return client
 
def start_heartbeat(source, stop):
    def worker():
        client = producer()
        while not stop.is_set():
            try:
                send(client, "systems.heartbeat", source,
                     event(source, "heartbeat", {"status": "alive"}))
            except Exception:
                logging.exception("Heartbeat delivery failed")
            stop.wait(3)
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread
