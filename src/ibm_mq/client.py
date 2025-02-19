import asyncio
from asyncio import Event

from src.bindings.connection import Connection


import pymqi

from src.common.log import get_logger
from src.ibm_mq.config import Config
from pymqi import QueueManager, Queue

from src.ibm_mq.exceptions import IBMMQConnectionError


class IBMMQClient(Connection):
    def __init__(self, config: Config):
        self.config: Config = config
        self.logger = get_logger(
            f"ibmmq.{self.config.binding_name}.{self.config.binding_type}"
        )
        self.queue_manager: QueueManager | None = None
        self.queue: Queue | None = None
        self.is_polling = False
        self.stop_event: Event = Event()
        self.is_connected = False
        self.polling_task = None

    async def start(self):
        self._connect()

    async def stop(self):
        if self.is_polling:
            self.stop_event.set()
        self._disconnect()

    def _connect(self):
        try:
            cd = pymqi.CD()
            cd.ChannelName = self.config.channel_name.encode("utf-8")
            cd.ConnectionName = self.config.connection_string.encode("utf-8")
            cd.ChannelType = pymqi.CMQC.MQCHT_CLNTCONN
            cd.TransportType = pymqi.CMQC.MQXPT_TCP

            connect_options = pymqi.CMQC.MQCNO_HANDLE_SHARE_BLOCK
            sco = None
            if self.config.ssl:
                cd.SSLCipherSpec = self.config.ssl_cipher_spec.encode("utf-8")
                sco = pymqi.SCO()
                sco.KeyRepository = self.config.key_repo_location.encode("utf-8")

            self.queue_manager = pymqi.QueueManager(name=None)

            connect_params = {
                "name": self.config.queue_manager,
                "cd": cd,
                "opts": connect_options,
                "user": self.config.username.encode("utf-8"),
                "password": (
                    self.config.password.encode("utf-8") if self.config.password else ""
                ),
            }

            if sco is not None:
                connect_params["sco"] = sco

            self.queue_manager.connect_with_options(**connect_params)

        except Exception as e:
            self.logger.exception(f"Error Connecting to queue manager: {str(e)}")
            raise IBMMQConnectionError(
                f"Error Connecting to queue manager, reason: {str(e)}"
            )
        try:
            open_options = pymqi.CMQC.MQOO_INPUT_AS_Q_DEF | pymqi.CMQC.MQOO_OUTPUT
            self.queue = pymqi.Queue(
                self.queue_manager, self.config.queue_name.encode("utf-8"), open_options
            )
        except Exception as e:
            self.logger.error(f"Error Connecting to queue: {str(e)}")
            raise IBMMQConnectionError(f"Error Connecting to queue, reason: {str(e)}")
        self.is_connected = True
        self.logger.info("Connected to IBM MQ")

    def _disconnect(self):
        try:
            if not self.is_connected:
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

    async def poll(self, callback):
        if not self.is_connected:
            self.logger.error("Not connected to IBM MQ")
            raise IBMMQConnectionError("Not connected to IBM MQ")
        if callback is None:
            self.logger.error(
                "Callback function not provided"
            )  #     raise ValueError("Callback function not provided")

        async def _process():
            md = pymqi.MD()
            gmo = pymqi.GMO()
            gmo.Options = pymqi.CMQC.MQGMO_WAIT | pymqi.CMQC.MQGMO_FAIL_IF_QUIESCING
            gmo.WaitInterval = self.config.poll_interval_ms

            self.logger.info(
                f"Polling for messages every {self.config.poll_interval_ms}ms"
            )

            while not self.stop_event.is_set():
                try:
                    if self.config.receiver_mode == "rfh2":
                        message = await asyncio.to_thread(
                            self.queue.get_rfh2, None, md, gmo
                        )
                    elif self.config.receiver_mode == "no_rfh2":
                        message = await asyncio.to_thread(
                            self.queue.get_no_rfh2, None, md, gmo
                        )
                    elif (
                        self.config.receiver_mode == "default"
                        or self.config.receiver_mode is None
                        or self.config.receiver_mode == ""
                    ):
                        message = await asyncio.to_thread(self.queue.get, None, md, gmo)
                    else:
                        self.logger.error(
                            f"Invalid receiver mode: {self.config.receiver_mode} values can be 'rfh2', 'no_rfh2', 'default'"
                        )
                        raise IBMMQConnectionError(
                            f"Invalid receiver mode: {self.config.receiver_mode} values can be 'rfh2', 'no_rfh2', 'default'"
                        )
                    if self.config.log_received_messages:
                        self.logger.info(
                            f"Received Message:\n{gmo.__str__()}\n{md.__str__()}\nMessage:{message}"
                        )
                    try:
                        self.logger.info("Received message, calling kubemq target")
                        await callback(message)
                        self.logger.info("Messaged processed successfully")
                    except Exception as callback_error:
                        self.logger.error(
                            f"Error in sending to kubemq target: {str(callback_error)}"
                        )
                    md.MsgId = pymqi.CMQC.MQMI_NONE
                    md.CorrelId = pymqi.CMQC.MQCI_NONE
                    md.GroupId = pymqi.CMQC.MQGI_NONE

                except pymqi.MQMIError as e:
                    if (
                        e.comp == pymqi.CMQC.MQCC_FAILED
                        and e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE
                    ):
                        await asyncio.sleep(0.1)  # Yield to other coroutines
                    else:
                        self.logger.error(f"Error polling for message: {str(e)}")
                except Exception as e:
                    self.logger.error(f"Error polling for message: {str(e)}")

            self.logger.info("Polling stopped")

        self.polling_task = asyncio.create_task(_process())
        return self.polling_task

    async def send_message(self, message: bytes):
        if not self.is_connected:
            self.logger.error("Not connected to IBM MQ")
            raise IBMMQConnectionError("Not connected to IBM MQ")

        message_str = message.decode("utf-8")
        if self.config.log_sent_messages:
            self.logger.info(f"Sending message: {message_str}")

        async def _send_message():
            try:
                self.logger.info("Sending message to IBM MQ")
                if self.config.sender_mode == "rfh2":
                    await asyncio.to_thread(self.queue.put_rfh2, message_str)
                elif self.config.sender_mode == "custom":
                    md = pymqi.MD()
                    md.Format = self.config.get_md_format()
                    if self.config.message_ccsid > 0:
                        md.CodedCharSetId = self.config.message_ccsid
                    await asyncio.to_thread(self.queue.put, message_str, md)
                elif (
                    self.config.sender_mode == "default"
                    or self.config.sender_mode is None
                    or self.config.sender_mode == ""
                ):
                    await asyncio.to_thread(self.queue.put, message_str)
                else:
                    self.logger.error(
                        f"Invalid sender mode: {self.config.sender_mode} values can be 'rfh2', 'custom', 'default'"
                    )
                    raise IBMMQConnectionError(
                        f"Invalid sender mode: {self.config.sender_mode} values can be 'rfh2', 'custom', 'default'"
                    )
                self.logger.info("Message sent successfully")
            except Exception as e:
                self.logger.error(f"Error sending message: {str(e)}")
                raise IBMMQConnectionError(f"Error sending message, reason: {str(e)}")

        asyncio.create_task(_send_message())
