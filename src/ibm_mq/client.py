import asyncio
import threading
from asyncio import Event, Task
from typing import Optional, Callable, Any, Coroutine, Union
import time
import random

from src.bindings.connection import Connection

import pymqi

from src.common.log import get_logger
from src.ibm_mq.config import Config
from src.ibm_mq.strategies import get_receiver_strategy, get_sender_strategy
from src.ibm_mq.error_classification import (
    classify_error,
    get_retry_recommendation,
    get_error_message,
    ErrorType,
)
from pymqi import QueueManager, Queue

from src.ibm_mq.exceptions import IBMMQConnectionError
from src.metrics.binding import BindingMetricsHelper


class IBMMQClient(Connection):
    """IBM MQ client implementation for connecting to and interacting with IBM MQ services.

    This class handles the complete lifecycle of IBM MQ connections including establishing
    connections, sending and receiving messages, and handling reconnection in case of
    connection failures. It implements the Connection interface to provide standardized
    interaction with the messaging system.

    Attributes:
        config (Config): Configuration for the IBM MQ connection and messaging
        logger: Logger instance for this client
        queue_manager (QueueManager): IBM MQ queue manager connection
        queue (Queue): IBM MQ queue for sending/receiving messages
        is_polling (bool): Flag indicating if the client is actively polling for messages
        stop_event (Event): Event to signal stopping of polling activities
        is_connected (bool): Connection status flag
        polling_task: Asyncio task for message polling
        reconnect_attempts (int): Counter for reconnection attempts
        heartbeat_task: Asyncio task for periodic heartbeat
        heartbeat_interval: Interval between heartbeats in seconds
    """

    def __init__(self, config: Config, metrics_helper: BindingMetricsHelper) -> None:
        """Initialize the IBM MQ client with the provided configuration and metrics helper.

        Args:
            config (Config): Configuration object containing IBM MQ connection parameters
            metrics_helper (BindingMetricsHelper): Helper instance for reporting metrics
        """
        self.config: Config = config
        self.metrics = metrics_helper
        self.logger = get_logger(
            f"ibmmq.{self.config.binding_name}.{self.config.binding_type}",
            self.config.queue_name,
        )
        self.queue_manager: Optional[QueueManager] = None
        self.queue: Optional[Queue] = None
        self.is_polling: bool = False
        self.stop_event: Event = Event()
        self.is_connected: bool = False

        self.polling_task: Optional[Task] = None
        self.reconnect_attempts: int = 0

        # Heartbeat for non-poll mode clients
        self.heartbeat_task: Optional[Task] = None
        self.heartbeat_interval: int = 5  # Heartbeat every 15 seconds

    async def start(self) -> None:
        """Start the IBM MQ client by establishing a connection to the MQ server.

        This method initializes the connection to IBM MQ using the configured parameters.
        It also starts the health check and heartbeat tasks for connection monitoring.

        Raises:
            IBMMQConnectionError: If connection to IBM MQ fails
        """
        self._connect()

        # Start the heartbeat task (especially important for non-poll mode)
        self.heartbeat_task = asyncio.create_task(self._periodic_heartbeat())

    async def stop(self) -> None:
        """Stop the IBM MQ client and release all resources.

        This method signals any polling operations to stop and closes the connection
        to IBM MQ, ensuring proper cleanup of resources.
        """

        if self.is_polling:
            self.stop_event.set()
        # Cancel the heartbeat task if running
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        self._disconnect()

    def _connect(self) -> None:
        """Establish a connection to the IBM MQ server.

        This method sets up the connection to the IBM MQ queue manager and opens
        the specified queue for sending/receiving messages, handling various
        connection parameters including SSL if configured.

        Raises:
            IBMMQConnectionError: If connection to queue manager or queue fails
        """
        try:
            # If already connected, disconnect first

            if self.is_connected:
                self._disconnect()

            cd = pymqi.CD()
            cd.ChannelName = self.config.channel_name.encode("utf-8")
            cd.ConnectionName = self.config.connection_string.encode("utf-8")
            cd.ChannelType = pymqi.CMQC.MQCHT_CLNTCONN
            cd.TransportType = pymqi.CMQC.MQXPT_TCP

            connect_options = pymqi.CMQC.MQCNO_HANDLE_SHARE_BLOCK
            sco: Optional[pymqi.SCO] = None
            if self.config.ssl:
                cd.SSLCipherSpec = self.config.ssl_cipher_spec.encode("utf-8")
                sco = pymqi.SCO()
                sco.KeyRepository = self.config.key_repo_location.encode("utf-8")

            self.queue_manager = pymqi.QueueManager(name=None)

            connect_params: dict[str, Any] = {
                "name": self.config.queue_manager,
                "cd": cd,
                "opts": connect_options,
                "user": self.config.username.encode("utf-8"),
                "password": (
                    self.config.password.encode("utf-8") if self.config.password else ""
                ),
                "HeartbeatInterval": 1,
            }
            if sco is not None:
                connect_params["sco"] = sco

            self.queue_manager.connect_with_options(**connect_params)

        except pymqi.MQMIError as e:
            error_msg = get_error_message(e.reason)
            self.logger.error(
                f"Error connecting to queue manager: {error_msg} (Reason: {e.reason})"
            )
            self.transition_to_disconnected(
                f"Error connecting to queue manager: {error_msg}"
            )
            raise IBMMQConnectionError(
                f"Error connecting to queue manager: {error_msg}"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to queue manager: {str(e)}")
            self.transition_to_disconnected(
                f"Unexpected error connecting to queue manager: {str(e)}"
            )

            raise IBMMQConnectionError(
                f"Unexpected error connecting to queue manager: {str(e)}"
            )

        try:
            open_options = pymqi.CMQC.MQOO_INPUT_AS_Q_DEF | pymqi.CMQC.MQOO_OUTPUT
            self.queue = pymqi.Queue(
                self.queue_manager, self.config.queue_name.encode("utf-8"), open_options
            )
        except pymqi.MQMIError as e:
            error_msg = get_error_message(e.reason)
            self.logger.error(
                f"Error connecting to queue: {error_msg} (Reason: {e.reason})"
            )
            self.transition_to_disconnected(f"Error connecting to queue: {error_msg}")
            # Close queue manager if already connected
            if self.queue_manager:
                try:
                    self.queue_manager.disconnect()
                except:
                    pass
            raise IBMMQConnectionError(f"Error connecting to queue: {error_msg}")
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to queue: {str(e)}")
            self.transition_to_disconnected(
                f"Unexpected error connecting to queue: {str(e)}"
            )
            # Close queue manager if already connected
            if self.queue_manager:
                try:
                    self.queue_manager.disconnect()
                except:
                    pass
            raise IBMMQConnectionError(
                f"Unexpected error connecting to queue: {str(e)}"
            )

        # Connection successful - transition to connected state
        self.transition_to_connected()
        self.logger.info("Connected to IBM MQ")

    def _disconnect(self) -> None:
        """Disconnect from the IBM MQ server and clean up resources.

        This method closes the queue and disconnects from the queue manager,
        ensuring that resources are properly released regardless of errors.
        """
        try:
            if not self.is_connected:
                return
            if hasattr(self, "queue") and self.queue:
                self.queue.close()
                self.queue = None
            if hasattr(self, "queue_manager") and self.queue_manager:
                self.queue_manager.disconnect()
                self.queue_manager = None
        except Exception as e:
            self.logger.error(
                f"Error disconnecting from queue and queue manager: {str(e)}"
            )
        finally:
            # Always mark as disconnected
            self.transition_to_disconnected("Client disconnected")
            self.logger.info("Disconnected from IBM MQ")

    async def _reconnect(self) -> bool:
        """Attempt to reconnect to IBM MQ with backoff strategy.

        This method implements the reconnection logic with a configurable delay
        between attempts, using exponential backoff for retries. It tracks
        reconnection attempts and properly updates the client state.

        Returns:
            bool: True if reconnection was successful, False otherwise
        """

        self.reconnect_attempts += 1
        self.transition_to_reconnecting()
        self.logger.info(
            f"Attempting to reconnect (attempt {self.reconnect_attempts}) in {self.config.reconnect_delay:.2f} second(s)..."
        )

        await asyncio.sleep(self.config.reconnect_delay)

        try:
            # Perform the actual connection
            self._connect()
            self.logger.info("Successfully reconnected to IBM MQ")
            self.transition_to_connected()
            return True
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Failed to reconnect: {error_msg}")
            self.transition_to_disconnected(f"Reconnection failed: {error_msg}")
            return False

    def extract_xml_payload(self, message_bytes: Union[bytes, str]) -> bytes:
        """Extract XML payload from a message.

        This function looks for XML content in a message and extracts it if found.

        Args:
            message_bytes: Message content which may contain XML

        Returns:
            bytes: XML content if found, or the original message
        """
        # Convert bytes to string for processing
        if isinstance(message_bytes, bytes):
            message_str = message_bytes.decode("utf-8", errors="replace")
        else:
            message_str = str(message_bytes)

        # Look for the XML declaration which starts the payload
        xml_start_marker = "<?xml"
        xml_start_index = message_str.find(xml_start_marker)

        if xml_start_index == -1:
            # No XML declaration found, return original message
            if isinstance(message_bytes, bytes):
                return message_bytes
            return message_bytes.encode("utf-8")

        # Extract everything from the XML start to the end
        xml_payload = message_str[xml_start_index:]

        # Convert back to bytes for return
        return xml_payload.encode("utf-8")

    async def poll(
        self, callback: Callable[[bytes], Coroutine[Any, Any, None]]
    ) -> Task:
        """Poll for messages from IBM MQ and process them.

        Args:
            callback: Function to call with each received message

        Returns:
            Asyncio task that is running the polling
        """
        # Reset polling state
        self.should_stop_polling = False
        self.is_polling = True
        self.logger.info("Starting to poll for messages")

        # Clean up any existing task
        if (
            hasattr(self, "polling_task")
            and self.polling_task
            and not self.polling_task.done()
        ):
            self.logger.warning("Existing polling task found, cancelling it")
            self.polling_task.cancel()

        async def _process() -> None:
            connection_broken = False

            while self.is_polling and not self.should_stop_polling:
                # If connection is broken, attempt to reconnect
                if connection_broken or not self.is_connected:
                    self.logger.error(
                        "Connection is broken or not established, attempting to reconnect"
                    )
                    self.transition_to_reconnecting()
                    reconnected = await self._reconnect()
                    if not reconnected:
                        self.logger.error("Failed to reconnect, retrying after delay")
                        await asyncio.sleep(self.config.reconnect_delay)
                        continue
                    else:
                        connection_broken = False

                # Reset the connection_broken flag if we got here
                try:
                    # Get an appropriate receiver strategy based on the configuration
                    try:
                        receiver_strategy = get_receiver_strategy(
                            self.config.receiver_mode
                        )
                    except ValueError as e:
                        self.logger.error(str(e))
                        # Configuration errors need manual intervention, so sleep longer
                        await asyncio.sleep(5.0)
                        continue

                    # Prepare message descriptor and get-message options
                    md: pymqi.MD = pymqi.MD()
                    gmo: pymqi.GMO = pymqi.GMO()
                    gmo.Options = (
                        pymqi.CMQC.MQGMO_WAIT | pymqi.CMQC.MQGMO_FAIL_IF_QUIESCING
                    )
                    gmo.WaitInterval = self.config.poll_interval_ms

                    if not hasattr(self, "poll_log_shown"):
                        self.logger.info(
                            f"Polling for messages every {self.config.poll_interval_ms}ms"
                        )
                        setattr(self, "poll_log_shown", True)

                    try:
                        message = await receiver_strategy.receive_message(
                            self.queue, md, gmo
                        )

                        cleaned_message: bytes = self.extract_xml_payload(message)
                        if self.config.log_received_messages:
                            self.logger.debug(f"Received message")
                            self.logger.trace(
                                f"\n{gmo.__str__()}\n{md.__str__()}\n{cleaned_message}"
                            )
                        await self.metrics.increment_received_message_and_volume(
                            len(cleaned_message), 1
                        )
                        try:
                            await callback(cleaned_message)
                        except Exception as callback_error:
                            self.logger.error(
                                f"Error in sending to kubemq target: {str(callback_error)}"
                            )
                            self.last_error = callback_error

                        # Reset message descriptors for next get
                        md.MsgId = pymqi.CMQC.MQMI_NONE
                        md.CorrelId = pymqi.CMQC.MQCI_NONE
                        md.GroupId = pymqi.CMQC.MQGI_NONE

                    except pymqi.MQMIError as e:
                        error_type = classify_error(e.reason)
                        error_msg = get_error_message(e.reason)
                        retry_rec = get_retry_recommendation(e.reason)
                        await self.metrics.increment_received_error(1)
                        if error_type == ErrorType.TRANSIENT:
                            # For transient errors, just wait and retry
                            if (
                                e.reason != pymqi.CMQC.MQRC_NO_MSG_AVAILABLE
                            ):  # Don't log no message available
                                self.logger.debug(
                                    f"Transient error: {error_msg} (Reason: {e.reason})"
                                )
                            await asyncio.sleep(0.1)

                        elif error_type == ErrorType.CONNECTION:
                            # For connection errors, trigger a reconnection
                            self.logger.error(
                                f"Connection error: {error_msg} (Reason: {e.reason}). Will attempt to reconnect."
                            )

                            connection_broken = True
                            self.is_connected = False
                            self.last_error = e

                        elif error_type == ErrorType.SHUTDOWN:
                            # For shutdown errors, wait longer before reconnecting
                            self.logger.warning(
                                f"Queue manager shutting down: {error_msg} (Reason: {e.reason}). Will attempt to reconnect after delay."
                            )
                            connection_broken = True
                            self.is_connected = False
                            self.last_error = e
                            await asyncio.sleep(retry_rec["retry_delay"])

                        else:
                            # For permanent or configuration errors, log error but keep trying
                            self.logger.error(
                                f"Error polling for message: {error_msg} (Reason: {e.reason})"
                            )
                            self.last_error = e
                            await asyncio.sleep(
                                1.0
                            )  # Slightly longer delay for permanent errors

                    except Exception as e:
                        self.logger.error(
                            f"Unexpected error polling for message: {str(e)}"
                        )
                        await self.metrics.increment_received_error(1)
                        self.last_error = e
                        # Mark connection as broken for most exceptions to trigger reconnection
                        if self.is_connected:
                            connection_broken = True
                            self.is_connected = False
                except Exception as e:
                    self.logger.error(f"Error in polling loop: {str(e)}")
                    self.last_error = e
                    # Mark connection as broken for most exceptions to trigger reconnection
                    if self.is_connected:
                        connection_broken = True
                        self.is_connected = False
                    await asyncio.sleep(
                        1.0
                    )  # Add delay to avoid spinning in case of repeated errors

            self.is_polling = False
            self.logger.info("Polling stopped")

        self.polling_task = asyncio.create_task(_process())
        return self.polling_task

    async def send_message(self, message: bytes) -> None:
        """Send a message to the IBM MQ queue.

        This method sends a message to the IBM MQ queue with enhanced connection
        validation and recovery. It will attempt reconnection if not connected,
        and directly validate the connection before sending to ensure reliability.

        Args:
            message: The message content to send to the queue

        Raises:
            IBMMQConnectionError: If not connected to IBM MQ and reconnection fails
        """
        # If not connected, try to reconnect first
        if not self.is_connected:
            self.logger.info(
                "Not connected to IBM MQ, attempting reconnection before sending"
            )
            reconnected = await self._reconnect()
            if not reconnected:
                raise IBMMQConnectionError(
                    "Not connected to IBM MQ, reconnection failed"
                )

        # Explicitly validate connection before sending
        connection_valid = await self.test_connection_directly()
        if not connection_valid:
            self.logger.warning(
                "Connection validation failed before sending, attempting reconnection"
            )
            self.transition_to_disconnected(
                "Connection validation failed before send operation"
            )
            reconnected = await self._reconnect()
            if not reconnected:
                await self.metrics.increment_sent_error(1)
                raise IBMMQConnectionError(
                    "Connection validation failed before send operation"
                )

        # Convert bytes to string for processing by the strategy
        message_str = message.decode("utf-8")
        if self.config.log_sent_messages:
            self.logger.info(f"Sending message: {message_str}")

        # Now proceed with sending using the strategy pattern
        async def _send_message():
            try:
                # Get the appropriate sender strategy based on the configuration
                try:
                    sender_strategy = get_sender_strategy(self.config.sender_mode)
                except ValueError as e:
                    self.logger.error(str(e))
                    raise IBMMQConnectionError(str(e))

                # Use the strategy to send the message
                self.logger.debug("Sending message to IBM MQ")
                self.logger.trace(f"{message_str}")
                await sender_strategy.send_message(self.queue, message_str, self.config)
                await self.metrics.increment_sent_message_and_volume(len(message), 1)
            except pymqi.MQMIError as e:
                error_msg = get_error_message(e.reason)
                error_type = classify_error(error_msg)
                self.logger.error(
                    f"Error sending message to IBM MQ: {error_msg} (Reason: {e.reason})"
                )
                await self.metrics.increment_sent_error(1)
                # For connection-related errors, attempt reconnection
                if (
                    error_type == ErrorType.CONNECTION
                    or error_type == ErrorType.SHUTDOWN
                ):
                    self.transition_to_disconnected(f"Send failed: {error_msg}")
                    reconnected = await self._reconnect()
                    if reconnected:
                        # Retry the send after reconnection
                        await self.send_message(message)
                        return

                raise IBMMQConnectionError(
                    f"Error sending message to IBM MQ: {error_msg}"
                )
            except Exception as e:
                self.logger.error(
                    f"Unexpected error sending message to IBM MQ: {str(e)}"
                )
                await self.metrics.increment_sent_error(1)
                raise IBMMQConnectionError(
                    f"Unexpected error sending message to IBM MQ: {str(e)}"
                )

        await _send_message()

    async def is_healthy(self) -> bool:
        """Check if the IBM MQ client is healthy.

        Returns:
            bool: True if healthy, False otherwise
        """

        return self.is_connected

    async def test_connection_directly(self) -> bool:
        """Test connection directly without relying on is_connected state.

        This method performs a direct test of the queue manager connection
        independent of current client state variables. This ensures more
        accurate detection of actual connection status.

        Returns:
            bool: True if connection is active, False otherwise
        """
        if not self.queue_manager:
            return False

        try:
            _ = self.queue_manager.inquire(pymqi.CMQC.MQCA_Q_MGR_NAME)
            return True
        except Exception as e:
            self.logger.error(f"Direct connection test failed: {str(e)}")
            return False

    def transition_to_connected(self) -> None:
        """Transition to connected state.

        Centralized method to ensure all state variables are updated consistently
        when transitioning to connected state.
        """

        self.is_connected = True
        self.reconnect_attempts = 0
        self.metrics.set_connection_status_sync(self.is_connected)
        self.logger.info("State transition: disconnected -> connected")

    def transition_to_disconnected(self, reason: str) -> None:
        """Transition to disconnected state.

        Centralized method to ensure all state variables are updated consistently
        when transitioning to disconnected state.

        Args:
            reason: The reason for disconnection
        """
        if self.is_connected:  # Only log if actually changing state
            self.logger.info(
                f"State transition: connected -> disconnected (Reason: {reason})"
            )

        self.is_connected = False
        self.metrics.set_connection_status_sync(self.is_connected)

    def transition_to_reconnecting(self) -> None:
        """Transition the client to reconnecting state."""
        self.is_connected = False
        self.logger.info("Transitioning to reconnecting state")
        self.metrics.set_connection_status_sync(self.is_connected)

    async def _periodic_heartbeat(self) -> None:
        """Periodic heartbeat task that runs periodically to detect connection issues.

        This method performs a heartbeat check of the IBM MQ connection at a regular interval.
        If the connection is broken, it attempts to reconnect.
        """
        while not self.stop_event.is_set():
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # Skip heartbeat check if we're already trying to reconnect
                if self.is_connected and not self.stop_event.is_set():
                    # Check health status
                    is_healthy = await self.is_healthy()

                    # If not healthy but we think we're connected, try to reconnect
                    if not is_healthy and self.is_connected:
                        self.logger.warning(
                            "Periodic heartbeat detected connection issue. Attempting to reconnect..."
                        )
                        # Set connection status to disconnected
                        self.is_connected = False
                        # Try to reconnect
                        asyncio.create_task(self._reconnect())
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic heartbeat: {str(e)}")
                await asyncio.sleep(1)  # Wait a bit before retrying on error
