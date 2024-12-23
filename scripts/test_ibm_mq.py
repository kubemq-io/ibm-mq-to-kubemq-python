import asyncio

import anyio
from src.common.log import get_logger
from src.ibm_mq.client import IBMMQClient
from src.ibm_mq.config import Config


logger = get_logger("main")


def get_client():
    config: Config = Config(
        host_name="84.200.100.229",
        port_number=32384,
        channel_name="SECUREAPP.CHANNEL",
        queue_manager="secureapphelm",
        queue_name="SECUREAPP.QUEUE",
        username="admin",
        password="Passw0rd",
        poll_interval_ms=100,
    )
    client: IBMMQClient = IBMMQClient()
    client.init(config)
    return client


async def get_callback(message):
    print(f"Received message: {message}")


async def main():
    client = get_client()
    try:
        # client.test()
        await client.start()
        # await client.send_message(b"Hello World")
        # stop_event = Event()
        await client.poll(get_callback)
        await asyncio.sleep(30)
        # stop_event.set()
        await client.stop()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    anyio.run(main)
