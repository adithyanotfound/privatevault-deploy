import json
from aiokafka import AIOKafkaProducer

class KafkaBus:

    def __init__(self, bootstrap="localhost:9092"):
        self.bootstrap = bootstrap
        self.producer = None

    async def start(self):
        self.producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap)
        await self.producer.start()

    async def publish(self, topic, payload):

        if not self.producer:
            return

        await self.producer.send_and_wait(
            topic,
            json.dumps(payload).encode()
        )
