import asyncio
import os
from asyncio import Event


from kubemq.queues import Client, QueueMessage

from src.bindings.connection import Connection
from src.kubemq.exceptions import KubeMQConnectionError

os.environ.setdefault("MQ_FILE_PATH", "C:/Program Files (x86)/IBM/WebSphere MQ")

from src.common.log import get_logger
from src.ibm_mq.config import Config


class KubeMQClient(Connection):
    def __init__(self, config: Config):
        self.config: Config = config
        self.logger = get_logger(
            f"kubemq.{self.config.binding_name}.{self.config.binding_type}"
        )
        self.client: Client | None = None
        self.is_polling = False
        self.stop_event: Event = Event()
        self.is_connected = False
        self.polling_task: asyncio.Task | None = None

    async def start(self):
        self._connect()

    async def stop(self):
        if self.is_polling:
            self.stop_event.set()
        self._disconnect()

    def _connect(self):
        try:
            self.client = Client(
                address=self.config.address,
                client_id=self.config.client_id,
            )
        except Exception as e:
            self.logger.error(f"Error connecting to kubemq server: {str(e)}")
            raise KubeMQConnectionError(
                f"Error Connecting to queue manager, reason: {str(e)}"
            )
        self.is_connected = True
        self.logger.info("Connected to Kubemq")

    def _disconnect(self):
        try:
            if not self.is_connected:
                return
            # self.client.close()
        except Exception as e:
            self.logger.exception(
                f"Error disconnecting from Kubemq server, reason: {str(e)}"
            )
            raise KubeMQConnectionError(
                f"Error disconnecting from Kubemq server, reason: {str(e)}"
            )

        self.logger.info("Disconnected from Kubemq")

    async def poll(self, callback):
        if not self.is_connected:
            self.logger.error("Not connected to Kubemq")
            raise KubeMQConnectionError("Not connected to Kubemq")
        if callback is None:
            self.logger.error(
                "Callback function not provided"
            )  #     raise ValueError("Callback function not provided")

        async def _process():
            while not self.stop_event.is_set():
                try:
                    poll_response = await asyncio.to_thread(
                        self.client.receive_queues_messages,
                        channel=self.config.queue_name,
                        max_messages=1,
                        wait_timeout_in_seconds=self.config.poll_interval_seconds,
                    )
                    if poll_response.is_error:
                        self.logger.error(
                            f"Error polling messages: {poll_response.error}"
                        )
                        await asyncio.sleep(self.config.poll_interval_seconds)
                        continue
                    if len(poll_response.messages) == 0:
                        continue

                    for message in poll_response.messages:
                        try:
                            self.logger.info(f"Received message: {message.body}")
                            await callback(message.body)
                            is_message_processed = True
                        except Exception as callback_error:
                            self.logger.error(
                                f"Error in callback function: {str(callback_error)}, rejecting message"
                            )
                            is_message_processed = False

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

    async def send_message(self, message: bytes):
        if not self.is_connected:
            self.logger.error("Not connected to Kubemq")
            raise KubeMQConnectionError("Not connected to Kubemq")

        async def _send_message():
            try:
                self.logger.info("Sending message to kubemq")
                result = await asyncio.to_thread(
                    self.client.send_queues_message,
                    QueueMessage(
                        body=message,
                        channel=self.config.queue_name,
                    ),
                )
                self.logger.info("Message sent to kubemq")
                if result.is_error:
                    self.logger.error(f"Error sending message: {result.error}")
            except Exception as e:
                self.logger.error(f"Error sending message: {str(e)}")

        asyncio.create_task(_send_message())
