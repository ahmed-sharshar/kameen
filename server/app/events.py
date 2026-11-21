import asyncio
from collections import defaultdict
from . import db

subscribers = defaultdict(set)        # in memory: run the server as a single process

async def publish(conv_id, event):
    await db.add_event(conv_id, event)                # the audit log first
    for queue in list(subscribers[conv_id]):
        queue.put_nowait(event)

async def subscribe(conv_id):
    queue = asyncio.Queue()
    subscribers[conv_id].add(queue)
    try:
        while True:
            try:
                yield await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                yield None                            # the route sends a ping to keep the stream open
    finally:
        subscribers[conv_id].discard(queue)
