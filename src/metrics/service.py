import asyncio
import functools
from prometheus_client import Counter, Gauge, start_http_server

from src.common.log import get_logger

TOTAL_MESSAGES_COUNT = Counter(
    "total_messages_count",
    "Total number of messages sent and received",
    ["binding_name", "binding_type", "direction", "queue_name"],
)

TOTAL_MESSAGES_VOLUME = Counter(
    "total_messages_volume",
    "Total volume of messages sent and received",
    ["binding_name", "binding_type", "direction", "queue_name"],
)

TOTAL_ERRORS_COUNT = Counter(
    "total_errors_count",
    "Total number of errors",
    ["binding_name", "binding_type", "direction", "queue_name"],
)

CONNECTION_STATUS = Gauge(
    "connection_status",
    "Connection status of binding",
    ["binding_name", "binding_type", "queue_name"],
)


class MetricsService:
    def __init__(self, port: int):
        self.port = port
        self.logger = get_logger("metrics.service")

    def start(self):
        """Starts the Prometheus HTTP server in a background thread."""
        try:
            start_http_server(self.port)
            self.logger.info(f"Metrics server started on port {self.port}")
        except Exception as e:
            self.logger.error(
                f"Failed to start metrics server on port {self.port}: {e}"
            )
            # Depending on requirements, might want to raise or exit here

    def stop(self):
        """Placeholder for potential graceful shutdown logic."""
        # Note: prometheus_client doesn't provide a direct stop method for the server thread.
        # Usually, letting the daemon thread exit with the main process is sufficient.
        self.logger.info(
            "Metrics service stopping (Note: Prometheus server runs as daemon)."
        )

    async def _run_sync(self, func, *args, **kwargs):
        """Runs a synchronous function in a thread pool executor."""
        # For Python 3.9+
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

    async def increment_message_count(
        self,
        binding_name: str,
        binding_type: str,
        queue_name: str,
        direction: str,
        count: int = 1,
    ):
        """Increments the message count."""
        if direction not in ["sent", "received"]:
            self.logger.warning(
                f"Invalid direction '{direction}' for increment_message_count"
            )
            return
        try:
            await self._run_sync(
                TOTAL_MESSAGES_COUNT.labels(
                    binding_name=binding_name,
                    binding_type=binding_type,
                    direction=direction,
                    queue_name=queue_name,
                ).inc,  # Pass the method itself
                count,  # Argument for the inc method
            )
        except Exception as e:
            self.logger.error(f"Error incrementing message count: {e}")

    async def increment_message_volume(
        self,
        binding_name: str,
        binding_type: str,
        queue_name: str,
        direction: str,
        volume: int,
    ):
        """Increments the message volume."""
        if direction not in ["sent", "received"]:
            self.logger.warning(
                f"Invalid direction '{direction}' for increment_message_volume"
            )
            return
        try:
            await self._run_sync(
                TOTAL_MESSAGES_VOLUME.labels(
                    binding_name=binding_name,
                    binding_type=binding_type,
                    direction=direction,
                    queue_name=queue_name,
                ).inc,  # Pass the method itself
                volume,  # Argument for the inc method
            )
        except Exception as e:
            self.logger.error(f"Error incrementing message volume: {e}")

    async def increment_error_count(
        self,
        binding_name: str,
        binding_type: str,
        queue_name: str,
        direction: str,
        count: int = 1,
    ):
        """Increments the error count."""
        if direction not in ["sent", "received"]:
            self.logger.warning(
                f"Invalid direction '{direction}' for increment_error_count"
            )
            return
        try:
            await self._run_sync(
                TOTAL_ERRORS_COUNT.labels(
                    binding_name=binding_name,
                    binding_type=binding_type,
                    direction=direction,
                    queue_name=queue_name,
                ).inc,  # Pass the method itself
                count,  # Argument for the inc method
            )
        except Exception as e:
            self.logger.error(f"Error incrementing error count: {e}")

    async def set_connection_status(
        self, binding_name: str, binding_type: str, queue_name: str, status: bool
    ):
        """Sets the connection status gauge."""
        try:
            await self._run_sync(
                CONNECTION_STATUS.labels(
                    binding_name=binding_name,
                    binding_type=binding_type,
                    queue_name=queue_name,
                ).set,  # Pass the method itself
                int(status),  # Argument for the set method
            )
        except Exception as e:
            self.logger.error(f"Error setting connection status: {e}")

    def set_connection_status_sync(
        self, binding_name: str, binding_type: str, queue_name: str, status: bool
    ):
        """Sets the connection status gauge."""
        try:

            CONNECTION_STATUS.labels(
                binding_name=binding_name,
                binding_type=binding_type,
                queue_name=queue_name,
            ).set(
                int(status)
            )  # Argument for the set method

        except Exception as e:
            self.logger.error(f"Error setting connection status: {e}")
