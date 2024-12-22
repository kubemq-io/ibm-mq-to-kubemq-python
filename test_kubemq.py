import asyncio
import os
from asyncio import Event

import anyio
from src.common.log import get_logger
from src.ibm_mq.client import IBMMQClient
from src.kubemq.client import KubeMQClient
from src.kubemq.config import Config


logger = get_logger("main")


def get_client():
    config: Config = Config(
        address="localhost:50000",
        queue_name="q1",
        client_id="kubemq-client",
        poll_interval_seconds=1,
    )
    client: KubeMQClient = KubeMQClient()
    client.init(config)
    return client


async def get_callback(message):
    print(f"Received message: {message}")


async def main():
    client = get_client()
    try:
        # client.test()
        await client.start()
        await client.send_message(b"Hello World")
        # stop_event = Event()
        await client.poll(get_callback)
        await asyncio.sleep(30)
        # stop_event.set()
        await client.stop()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    anyio.run(main)
