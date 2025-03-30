import asyncio
from .service import MetricsService  # Assuming MetricsService is in service.py


class BindingMetricsHelper:
    """
    A helper class to simplify metric reporting for a specific binding context.

    Initializes with a MetricsService instance and the common labels
    (binding_name, binding_type, queue_name) for this binding.
    Provides simpler async methods to update metrics.
    """

    def __init__(
        self,
        metrics_service: MetricsService,
        binding_name: str,
        binding_type: str,
        queue_name: str,
    ):
        if not isinstance(metrics_service, MetricsService):
            raise TypeError("metrics_service must be an instance of MetricsService")
        if not all(
            isinstance(arg, str) for arg in [binding_name, binding_type, queue_name]
        ):
            raise TypeError(
                "binding_name, binding_type, and queue_name must be strings"
            )

        self._service = metrics_service
        self._binding_name = binding_name
        self._binding_type = binding_type
        self._queue_name = queue_name
        self._logger = metrics_service.logger  # Reuse logger from service

    async def increment_sent_message(self, count: int = 1):
        """Increments the count of messages sent."""
        if not isinstance(count, int) or count < 0:
            self._logger.warning(
                f"Invalid count '{count}' for increment_sent_message. Must be a non-negative integer."
            )
            return
        await self._service.increment_message_count(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            direction="sent",
            count=count,
        )

    async def increment_received_message(self, count: int = 1):
        """Increments the count of messages received."""
        if not isinstance(count, int) or count < 0:
            self._logger.warning(
                f"Invalid count '{count}' for increment_received_message. Must be a non-negative integer."
            )
            return
        await self._service.increment_message_count(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            direction="received",
            count=count,
        )

    async def increment_sent_volume(self, volume: int):
        """Increments the volume of messages sent."""
        if not isinstance(volume, int) or volume < 0:
            self._logger.warning(
                f"Invalid volume '{volume}' for increment_sent_volume. Must be a non-negative integer."
            )
            return
        await self._service.increment_message_volume(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            direction="sent",
            volume=volume,
        )

    async def increment_received_volume(self, volume: int):
        """Increments the volume of messages received."""
        if not isinstance(volume, int) or volume < 0:
            self._logger.warning(
                f"Invalid volume '{volume}' for increment_received_volume. Must be a non-negative integer."
            )
            return
        await self._service.increment_message_volume(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            direction="received",
            volume=volume,
        )

    async def increment_sent_message_and_volume(self, volume: int, count: int = 1):
        """Increments both the count and volume of messages sent with a single call."""
        if not isinstance(count, int) or count < 0:
            self._logger.warning(
                f"Invalid count '{count}' for increment_sent_message_and_volume. Must be a non-negative integer."
            )
            # Decide if we should proceed with volume if count is invalid, or return.
            # Let's return for simplicity.
            return
        if not isinstance(volume, int) or volume < 0:
            self._logger.warning(
                f"Invalid volume '{volume}' for increment_sent_message_and_volume. Must be a non-negative integer."
            )
            # If count was valid, should we still update it? Let's return for simplicity.
            return

        # Call both underlying service methods sequentially
        await self._service.increment_message_count(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            direction="sent",
            count=count,
        )
        await self._service.increment_message_volume(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            direction="sent",
            volume=volume,
        )

    async def increment_received_message_and_volume(self, volume: int, count: int = 1):
        """Increments both the count and volume of messages received with a single call."""
        if not isinstance(count, int) or count < 0:
            self._logger.warning(
                f"Invalid count '{count}' for increment_received_message_and_volume. Must be a non-negative integer."
            )
            return
        if not isinstance(volume, int) or volume < 0:
            self._logger.warning(
                f"Invalid volume '{volume}' for increment_received_message_and_volume. Must be a non-negative integer."
            )
            return

        # Call both underlying service methods sequentially
        await self._service.increment_message_count(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            direction="received",
            count=count,
        )
        await self._service.increment_message_volume(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            direction="received",
            volume=volume,
        )

    async def increment_sent_error(self, count: int = 1):
        """Increments the count of errors during sending."""
        if not isinstance(count, int) or count < 0:
            self._logger.warning(
                f"Invalid count '{count}' for increment_sent_error. Must be a non-negative integer."
            )
            return
        await self._service.increment_error_count(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            direction="sent",
            count=count,
        )

    async def increment_received_error(self, count: int = 1):
        """Increments the count of errors during receiving."""
        if not isinstance(count, int) or count < 0:
            self._logger.warning(
                f"Invalid count '{count}' for increment_received_error. Must be a non-negative integer."
            )
            return
        await self._service.increment_error_count(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            direction="received",
            count=count,
        )

    async def set_connection_status(self, status: bool):
        """Sets the current connection status."""
        if not isinstance(status, bool):
            self._logger.warning(
                f"Invalid status '{status}' for set_connection_status. Must be a boolean."
            )
            return
        await self._service.set_connection_status(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            status=status,
        )

    def set_connection_status_sync(self, status: bool):
        """Sets the current connection status."""
        if not isinstance(status, bool):
            self._logger.warning(
                f"Invalid status '{status}' for set_connection_status. Must be a boolean."
            )
            return
        self._service.set_connection_status_sync(
            binding_name=self._binding_name,
            binding_type=self._binding_type,
            queue_name=self._queue_name,
            status=status,
        )

    # Convenience properties
    @property
    def binding_name(self) -> str:
        return self._binding_name

    @property
    def binding_type(self) -> str:
        return self._binding_type

    @property
    def queue_name(self) -> str:
        return self._queue_name
