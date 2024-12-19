import os
from logging import Logger

os.environ.setdefault("MQ_FILE_PATH", "C:/Program Files (x86)/IBM/WebSphere MQ")
import pymqi
from asyncer import asyncify
from src.common.log import get_logger
from src.ibm_mq.config import Config
from pymqi import QueueManager, Queue

from src.ibm_mq.exceptions import IBMMQConnectionError


class IBMMQClient:
    def __init__(self):
        self.config: Config | None = None
        self.queue_manager: QueueManager | None = None
        self.logger: Logger | None = None
        self.queue: Queue | None = None

    @property
    def is_connected(self):
        return self.queue_manager is not None and self.queue is not None

    def init(self, config: Config):
        self.config = config
        self.logger = get_logger(
            f"ibmmq.client.{self.config.queue_manager}.{self.config.channel_name}.{self.config.queue_name}"
        )

    async def start(self):
        await asyncify(self._connect)()

    async def stop(self):
        await asyncify(self._disconnect)()

    def _connect(self):
        try:
            self.queue_manager: QueueManager = pymqi.connect(
                self.config.queue_manager,
                self.config.channel_name,
                self.config.connection_string,
                self.config.username,
                self.config.password,
            )
        except Exception as e:
            self.logger.error(f"Error Connecting to queue manager: {str(e)}")
            raise IBMMQConnectionError(
                f"Error Connecting to queue manager, reason: {str(e)}"
            )
        try:
            self.queue: Queue = pymqi.Queue(self.queue_manager, self.config.queue_name)
        except Exception as e:
            self.logger.error(f"Error Connecting to queue: {str(e)}")
            raise IBMMQConnectionError(f"Error Connecting to queue, reason: {str(e)}")

        self.logger.info("Connected to IBM MQ")

    def _disconnect(self):
        try:
            if self.queue_manager is None or self.queue is None:
                return
            self.queue.close()
            self.queue_manager.disconnect()
        except Exception as e:
            self.logger.error(
                f"Error disconnecting from queue and queue manager: {str(e)}"
            )
            raise IBMMQConnectionError(
                f"Error disconnecting from queue and queue manager, reason: {str(e)}"
            )

        self.logger.info("Disconnected from IBM MQ")
