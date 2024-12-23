import asyncio
import os
import signal

config_path = os.environ.get("CONFIG_PATH", "config.yaml")
os.environ.setdefault("MQ_FILE_PATH", os.path.join(os.getcwd(), "mq_files/windows"))

import anyio

from src.bindings.bindings import Bindings
from src.common.log import get_logger

logger = get_logger("main")
shutdown_event = asyncio.Event()


def handle_signal(sig, frame):
    """Handle termination signals from Kubernetes"""
    logger.info(f"Received signal {sig}. Starting graceful shutdown...")
    # Set the shutdown event - this will trigger the main loop to exit
    asyncio.get_event_loop().call_soon_threadsafe(shutdown_event.set)


async def main():
    bindings: Bindings | None = None
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, handle_signal)
        logger.info("Starting KubeMQ - IBM MQ bindings")
        bindings = Bindings(config_path)
        bindings.init()
        await bindings.start()
        # Wait for shutdown signal instead of infinite loop
        await shutdown_event.wait()

    except Exception as e:
        logger.exception(f"Fialed to start Kubemq - IBM MQ bindings: {str(e)}")
    finally:
        logger.info("Stopping Kubemq - IBM MQ bindings")
        if bindings:
            await bindings.stop()
        remaining_tasks = asyncio.all_tasks() - {asyncio.current_task()}
        if remaining_tasks:
            logger.info(f"Cancelling {len(remaining_tasks)} remaining tasks...")
            for task in remaining_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("Kubemq - IBM MQ bindings stopped")


if __name__ == "__main__":
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
