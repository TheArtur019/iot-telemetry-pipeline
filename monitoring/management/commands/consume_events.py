import json
from django.core.management.base import BaseCommand
from services.common import consumer
from monitoring.ingestion import save_event
 
class Command(BaseCommand):
    help = "Save Kafka events to PostgreSQL"
 
    def add_arguments(self, parser):
        parser.add_argument("--group", default="monitor-v1")
 
    def handle(self, *args, **options):
        reader = consumer(options["group"], [
            "telemetry.processed", "systems.heartbeat", "telemetry.invalid",
        ])
        try:
            while True:
                msg = reader.poll(1)
                if msg is None:
                    continue
                if msg.error():
                    raise RuntimeError(msg.error())
                save_event(json.loads(msg.value()))
                reader.commit(message=msg, asynchronous=False)
        except KeyboardInterrupt:
            pass
        finally:
            reader.close()
