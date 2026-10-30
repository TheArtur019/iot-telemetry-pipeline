from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaException, KafkaError
from services.common import BROKER
 
client = AdminClient({"bootstrap.servers": BROKER})
names = ["telemetry.raw", "telemetry.processed",
         "systems.heartbeat", "telemetry.invalid"]
futures = client.create_topics([
    NewTopic(name, num_partitions=1, replication_factor=1,
             config={"retention.ms": "86400000"})
    for name in names
])
for name, future in futures.items():
    try:
        future.result()
        print("Created:", name)
    except KafkaException as error:
        if error.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:
            raise
        print("Already exists:", name)
