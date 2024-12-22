import asyncio
import os
from asyncio import Event

import anyio

from src.bindings.binding import Binding
from src.common.log import get_logger
from src.ibm_mq.client import IBMMQClient
from src.kubemq.client import KubeMQClient
from src.kubemq.config import Config as KubeMQConfig
from src.ibm_mq.client import IBMMQClient
from src.ibm_mq.config import Config as IBMMQConfig

logger = get_logger("main")


def kubemq_target():
    config: KubeMQConfig = KubeMQConfig(
        address="localhost:50000",
        queue_name="from_ibm",
        client_id="kubemq-target",
    )
    client: KubeMQClient = KubeMQClient()
    client.init(config)
    return client


def kubemq_source():
    config: KubeMQConfig = KubeMQConfig(
        address="localhost:50000",
        queue_name="to_ibm",
        client_id="kubemq-client",
        poll_interval_seconds=1,
    )
    client: KubeMQClient = KubeMQClient()
    client.init(config)
    return client


def ibm_target():
    config: IBMMQConfig = IBMMQConfig(
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


def ibm_source():
    config: IBMMQConfig = IBMMQConfig(
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
    ibm_source_client = ibm_source()
    ibm_target_client = ibm_target()
    kubemq_target_client = kubemq_target()
    kubemq_source_client = kubemq_source()

    try:
        # client.test()
        # await kubemq_to_ibm.start()
        # print("Started kubemq_to_ibm")
        # await kubemq_target_client.start()
        await ibm_target_client.start()
        await ibm_source_client.start()
        await kubemq_target_client.start()
        await kubemq_source_client.start()

        await ibm_source_client.poll(get_callback)
        await kubemq_source_client.poll(get_callback)
        print("Started ibm_to_kubemq")

        await asyncio.sleep(30)
        # stop_event.set()
        # await ibm_to_kubemq.stop()
        # await kubemq_to_ibm.stop()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    anyio.run(main)
