import uuid
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from monitoring.ingestion import save_event
from monitoring.models import EventLog, MeasurementResult, SystemState
 
class IngestionTests(TestCase):
    def heartbeat(self, timestamp):
        return {"event_id": str(uuid.uuid4()), "source_id": "test",
                "event_type": "heartbeat", "event_time": timestamp.isoformat(),
                "payload": {"status": "alive"}}
 
    def test_duplicate_does_not_add_event(self):
        item = self.heartbeat(timezone.now())
        self.assertTrue(save_event(item))
        self.assertFalse(save_event(item))
        self.assertEqual(EventLog.objects.count(), 1)
 
    def test_old_heartbeat_does_not_roll_back_state(self):
        current = timezone.now()
        save_event(self.heartbeat(current))
        save_event(self.heartbeat(current - timedelta(minutes=5)))
        self.assertEqual(SystemState.objects.get().last_heartbeat, current)
 
    def test_failed_result_is_not_partially_saved(self):
        item = self.heartbeat(timezone.now())
        item["event_type"] = "result"
        with self.assertRaises(KeyError):
            save_event(item)
        self.assertEqual(EventLog.objects.count(), 0)
        self.assertEqual(MeasurementResult.objects.count(), 0)
 
    def test_api_marks_old_data_as_stale(self):
        save_event(self.heartbeat(timezone.now() - timedelta(seconds=45)))
        response = self.client.get("/api/state/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["systems"][0]["freshness"], "нет свежих данных")
        self.assertIsNone(data["warning_share"])
 
 
class ProcessorTests(TestCase):
    def measurement(self):
        return {"event_id": str(uuid.uuid4()), "schema_version": 1,
                "event_type": "measurement",
                "event_time": timezone.now().isoformat(),
                "payload": {"device_id": "motor-1", "value": 85,
                            "unit": "C", "is_anomaly": True}}
 
    def message(self, raw):
        from unittest.mock import Mock
        msg = Mock()
        msg.value.return_value = raw
        msg.topic.return_value = "telemetry.raw"
        msg.partition.return_value = 0
        msg.offset.return_value = 7
        return msg
 
    def test_bad_inputs_are_quarantined_before_commit(self):
        import json
        from unittest.mock import Mock, patch
        from services.processor import handle_message
        cases = [None, b"not json", b"\xff"]
        for field, value in [("device_id", "x" * 121),
                             ("is_anomaly", "false"),
                             ("unit", "F"), ("value", 10 ** 400)]:
            item = self.measurement()
            item["payload"][field] = value
            cases.append(json.dumps(item).encode())
        for raw in cases:
            with self.subTest(raw=repr(raw)[:50]):
                reader = Mock()
                msg = self.message(raw)
                def delivered(*args):
                    reader.commit.assert_not_called()
                    self.assertEqual(args[1], "telemetry.invalid")
                    save_event(args[3])
                with patch("services.processor.send", side_effect=delivered):
                    handle_message(msg, reader, Mock(), "test", 0, 80)
                reader.commit.assert_called_once_with(
                    message=msg, asynchronous=False)
 
    def test_failed_publication_never_commits(self):
        import json
        from unittest.mock import Mock, patch
        from services.processor import handle_message
        for raw in [None, json.dumps(self.measurement()).encode()]:
            reader = Mock()
            with patch("services.processor.send",
                       side_effect=RuntimeError("delivery failed")):
                with self.assertRaises(RuntimeError):
                    handle_message(self.message(raw), reader,
                                   Mock(), "test", 0, 80)
            reader.commit.assert_not_called()
 
    def test_uuid_variants_produce_one_logical_result(self):
        import json
        from unittest.mock import Mock, patch
        from services.processor import handle_message
        item = self.measurement()
        ids = []
        def delivered(*args):
            ids.append(args[3]["event_id"])
            save_event(args[3])
        with patch("services.processor.send", side_effect=delivered):
            for identifier in [item["event_id"],
                               item["event_id"].replace("-", "").upper()]:
                item["event_id"] = identifier
                handle_message(self.message(json.dumps(item).encode()),
                               Mock(), Mock(), "test", 0, 80)
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(MeasurementResult.objects.count(), 1)
        self.assertEqual(EventLog.objects.count(), 1)
