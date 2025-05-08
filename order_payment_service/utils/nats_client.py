from nats import NATS
import asyncio
import json

nats_client = NATS()

async def publish_order_created_event(order_event):
    try:
        print("Connecting to NATS to publish order_created event...", flush=True)
        await nats_client.connect(servers=["nats://nats:4222"])
        print(f"Publishing event to 'order_created': {order_event}", flush=True)
        await nats_client.publish("order_created", json.dumps(order_event).encode('utf-8'))
        print("Event published successfully!", flush=True)
        await nats_client.close() 
    except Exception as e:
        print(f"Error publishing order_created event to NATS: {e}", flush=True) 