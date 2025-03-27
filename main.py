import asyncio
import os

os.environ.setdefault("MQ_FILE_PATH", os.path.join(os.getcwd(), "mq_files/windows"))
import signal
import anyio
from src.bindings.bindings import Bindings
from src.common.log import get_logger
from src.api.app import APIServer

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
    api_server: APIServer | None = None
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, handle_signal)
        logger.info("Starting KubeMQ - IBM MQ bindings")
        bindings = Bindings(config_path)
        bindings.init()
        
        # Initialize and start the API server
        api_port = int(os.environ.get("API_PORT", "9000"))
        api_host = os.environ.get("API_HOST", "0.0.0.0")
        logger.info(f"Initializing API server on {api_host}:{api_port}")
        api_server = APIServer(bindings, host=api_host, port=api_port)
        
        # Start bindings and API server
        await bindings.start()
        await api_server.start()
        
        logger.info("KubeMQ - IBM MQ bindings and API server started successfully")
        
        # Wait for shutdown signal instead of infinite loop
        await shutdown_event.wait()

    except Exception as e:
        logger.exception(f"Failed to start Kubemq - IBM MQ bindings: {str(e)}")
    finally:
        # Graceful shutdown
        if api_server:
            await api_server.stop()
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
