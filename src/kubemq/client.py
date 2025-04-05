import asyncio
import os
from asyncio import Event


from kubemq.queues import Client, QueueMessage

from src.bindings.connection import Connection
from src.kubemq.exceptions import KubeMQConnectionError
from src.kubemq.config import Config

from src.common.log import get_logger
from src.metrics.binding import BindingMetricsHelper


class KubeMQClient(Connection):
    def __init__(self, config: Config, metrics_helper: BindingMetricsHelper):
        """Initialize the KubeMQ client with the provided configuration and metrics helper.

        Args:
            config (Config): Configuration object containing KubeMQ connection parameters
            metrics_helper (BindingMetricsHelper): Helper instance for reporting metrics
        """
        self.config: Config = config
        self.metrics = metrics_helper
        self.logger = get_logger(
            f"kubemq.{self.config.binding_name}.{self.config.binding_type}",
            self.config.queue_name,
        )
        self.client: Client | None = None
        self.is_polling = False
        self.stop_event: Event = Event()
        self.connection_status_lock = asyncio.Lock()
        self.is_connected = False
        self.polling_task: asyncio.Task | None = None

    async def start(self):
        await self._connect()

    async def stop(self):
        if self.is_polling:
            self.stop_event.set()
        await self._disconnect()

    async def _connect(self):
        try:
            self.client = Client(
                address=self.config.address,
                client_id=self.config.client_id,
            )
            await self.client.ping_async()
        except Exception as e:
            self.logger.error(f"Error connecting to kubemq server: {str(e)}")
            await self._update_connection_status(False)
            raise KubeMQConnectionError(
                f"Error Connecting to queue manager, reason: {str(e)}"
            )
        await self._update_connection_status(True)
        self.logger.info("Connected to Kubemq")

    async def _disconnect(self):
        try:
            await self._update_connection_status(False)
            self.logger.info("Disconnecting from Kubemq")
        except Exception as e:
            self.logger.exception(
                f"Error disconnecting from Kubemq server, reason: {str(e)}"
            )
            raise KubeMQConnectionError(
                f"Error disconnecting from Kubemq server, reason: {str(e)}"
            )

        self.logger.info("Disconnected from Kubemq")

    async def poll(self, callback):
        if callback is None:
            self.logger.error("Callback function not provided")  #
            raise ValueError("Callback function not provided")

        async def _process():
            while not self.stop_event.is_set():
                try:
                    poll_response = await self.client.receive_queues_messages_async(
                        channel=self.config.queue_name,
                        max_messages=1,
                        wait_timeout_in_seconds=self.config.poll_interval_seconds,
                    )
                    if poll_response.is_error:
                        self.logger.error(
                            f"Error polling messages: {poll_response.error}"
                        )
                        await self._update_connection_status(False)
                        await self.metrics.increment_received_error(1)
                        await asyncio.sleep(self.config.poll_interval_seconds)
                        continue

                    await self._update_connection_status(True)

                    if len(poll_response.messages) == 0:
                        continue
                    self.logger.debug(
                        f"Received {len(poll_response.messages)} messages"
                    )
                    for message in poll_response.messages:
                        try:
                            self.logger.trace(f"{message.body}")
                            await callback(message.body)
                            is_message_processed = True
                        except Exception as callback_error:
                            self.logger.error(
                                f"Error in callback function: {str(callback_error)}, rejecting message"
                            )
                            is_message_processed = False
                        await self.metrics.increment_received_message_and_volume(
                            len(message.body), 1
                        )
                        try:
                            if is_message_processed:
                                message.ack()
                            else:
                                message.reject()
                        except Exception as e:
                            self.logger.error(
                                f"Error acknowledging/rejecting message: {str(e)}"
                            )
                            await asyncio.sleep(self.config.poll_interval_seconds)

                except Exception as e:
                    self.logger.error(f"Error processing message: {str(e)}")
                    await asyncio.sleep(self.config.poll_interval_seconds)

        self.polling_task = asyncio.create_task(_process())
        return self.polling_task

    async def is_healthy(self) -> bool:
        with await self.connection_status_lock:
            return self.is_connected

    async def send_message(self, message: bytes):
        try:
            self.logger.debug(f"Sending message")
            self.logger.trace(f"{message}")
            result = await self.client.send_queues_message_async(
                QueueMessage(
                    body=message,
                    channel=self.config.queue_name,
                ),
            )
            if result.is_error:
                self.logger.error(f"Error sending message: {result.error}")
                await self._update_connection_status(False)
                await self.metrics.increment_sent_error(1)

            await self._update_connection_status(True)
            await self.metrics.increment_sent_message_and_volume(len(message), 1)
            self.logger.debug(f"Message sent successfully")
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")

    async def _update_connection_status(self, is_connected: bool):
        async with self.connection_status_lock:
            self.is_connected = is_connected
            await self.metrics.set_connection_status(is_connected)
