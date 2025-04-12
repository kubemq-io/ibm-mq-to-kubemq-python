import asyncio
import os

from src.metrics.service import MetricsService

os.environ.setdefault("MQ_FILE_PATH", os.path.join(os.getcwd(), "mq_files/windows"))
import signal
from src.bindings.bindings import Bindings
from src.common.log import get_logger


config_path = os.environ.get("CONFIG_PATH", "config.yaml")
logger = get_logger("main")
shutdown_event = asyncio.Event()


def handle_signal(sig, frame):
    """Handle termination signals from Kubernetes"""
    logger.info(f"Received signal {sig}. Starting graceful shutdown...")
    # Use a safer way to set the event
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # If no loop is running, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.call_soon_threadsafe(shutdown_event.set)


async def main():
    bindings: Bindings | None = None
    metrics_service = MetricsService(port=9000)
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, handle_signal)
        logger.info("Starting KubeMQ - Connectors bindings")
        bindings = Bindings(config_path, metrics_service)
        bindings.init()

        metrics_service.start()
        await bindings.start()

        logger.info("KubeMQ - Connectors bindings and API server started successfully")

        # Wait for shutdown signal instead of infinite loop
        await shutdown_event.wait()

    except Exception as e:
        logger.exception(f"Failed to start Kubemq - Connectors bindings: {str(e)}")
    finally:
        metrics_service.stop()
        if bindings:
            await bindings.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.exception(f"Unexpected error during shutdown: {str(e)}")
