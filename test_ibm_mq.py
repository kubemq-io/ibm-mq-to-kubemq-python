import asyncio
import os
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
    )
    client: IBMMQClient = IBMMQClient()
    client.init(config)
    return client


async def main():
    client = get_client()
    try:
        logger.info("Starting IBM MQ Client")
        await client.start()
        logger.info("IBM MQ Client started")

        await asyncio.sleep(5)
        await client.stop()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    anyio.run(main)
