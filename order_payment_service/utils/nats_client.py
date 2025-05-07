from nats import NATS
import asyncio
import json

nats_client = NATS()

async def publish_order_created_event(order_event):
    await nats_client.connect(servers=["nats://nats:4222"])
    await nats_client.publish("order_created", json.dumps(order_event).encode('utf-8'))
    await nats_client.close() 