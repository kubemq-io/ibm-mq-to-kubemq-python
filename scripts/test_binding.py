import asyncio

import anyio

from src.bindings.binding import Binding
from src.bindings.config import BindingConfig as BindingConfig, BindingType
from src.common.log import get_logger

from src.kubemq.config import Config as KubeMQConfig

from src.ibm_mq.config import Config as IBMMQConfig

logger = get_logger("main")

binding_kubemq_to_ibm = BindingConfig(
    name="kubemq_to_ibm",
    type=BindingType.KUBEMQ_TO_IBM_MQ,
    source=KubeMQConfig(
        address="localhost:50000",
        queue_name="to_ibm",
        client_id="kubemq-client",
        poll_interval_seconds=1,
    ),
    target=IBMMQConfig(
        host_name="host",
        port_number=32384,
        channel_name="SECUREAPP.CHANNEL",
        queue_manager="secureapphelm",
        queue_name="SECUREAPP.QUEUE",
        username="admin",
        password="Passw0rd",
        poll_interval_ms=100,
    ),
)

binding_ibm_to_kubemq = BindingConfig(
    name="ibm_to_kubemq",
    type=BindingType.IBM_MQ_TO_KUBEMQ,
    source=IBMMQConfig(
        host_name="host",
        port_number=32384,
        channel_name="SECUREAPP.CHANNEL",
        queue_manager="secureapphelm",
        queue_name="SECUREAPP.QUEUE",
        username="admin",
        password="Passw0rd",
        poll_interval_ms=100,
    ),
    target=KubeMQConfig(
        address="localhost:50000",
        queue_name="from_ibm",
        client_id="kubemq-target",
    ),
)


async def main():
    kubemq_to_ibm: Binding = Binding(binding_kubemq_to_ibm)
    ibm_to_kubemq: Binding = Binding(binding_ibm_to_kubemq)
    try:
        kubemq_to_ibm.init()
        ibm_to_kubemq.init()

        await kubemq_to_ibm.start()
        await ibm_to_kubemq.start()

        await asyncio.sleep(60)
        await ibm_to_kubemq.stop()
        await kubemq_to_ibm.stop()

    except Exception as e:
        logger.exception(f"Error: {str(e)}")


if __name__ == "__main__":
    anyio.run(main)
