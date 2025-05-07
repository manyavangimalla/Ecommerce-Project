from nats import NATS
import asyncio
import json

nats_client = NATS()

async def run(loop):
    await nats_client.connect(servers=["nats://nats:4222"], loop=loop)
    
    async def message_handler(msg):
        event = json.loads(msg.data.decode('utf-8'))
        print(f"Received event: {event}")

        if event['event_type'] == 'order_created':
            # Send notification for order creation
            user_id = event['user_id']
            order_id = event['order_id']
            send_notification(user_id, 'order_placed', {
                'order_id': order_id,
                'items': event['items']
            })

    await nats_client.subscribe("order_created", cb=message_handler)

loop = asyncio.get_event_loop()
loop.run_until_complete(run(loop)) 