import asyncio
from asyncio import Event, Task
from typing import Optional, Callable, Any, Coroutine, Union, Dict

from src.bindings.connection import Connection


import pymqi

from src.common.log import get_logger
from src.ibm_mq.config import Config
from src.ibm_mq.strategies import get_receiver_strategy, get_sender_strategy
from src.ibm_mq.error_classification import (
    classify_error, 
    get_retry_recommendation, 
    get_error_message,
    ErrorType
)
from src.ibm_mq.health import (
    perform_health_check,
    HealthCheckResult,
    HealthStatus
)
from pymqi import QueueManager, Queue

from src.ibm_mq.exceptions import IBMMQConnectionError


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
        max_reconnect_attempts (int): Maximum number of reconnection attempts (0 = unlimited)
    """
    def __init__(self, config: Config) -> None:
        """Initialize the IBM MQ client with the provided configuration.
        
        Args:
            config (Config): Configuration object containing IBM MQ connection parameters
        """
        self.config: Config = config
        self.logger = get_logger(
            f"ibmmq.{self.config.binding_name}.{self.config.binding_type}"
        )
        self.queue_manager: Optional[QueueManager] = None
        self.queue: Optional[Queue] = None
        self.is_polling: bool = False
        self.stop_event: Event = Event()
        self.is_connected: bool = False
        self.polling_task: Optional[Task] = None
        self.reconnect_attempts: int = 0
        self.max_reconnect_attempts: int = 0  # 0 means unlimited retries
        
        # Health tracking data
        self.last_error: Optional[Exception] = None
        self.last_health_check: Optional[HealthCheckResult] = None
        self.last_health_check_time: float = 0
        self.messages_sent: int = 0
        self.messages_received: int = 0
        self.message_send_errors: int = 0
        self.message_receive_errors: int = 0
        

    async def start(self) -> None:
        """Start the IBM MQ client by establishing a connection to the MQ server.
        
        This method initializes the connection to IBM MQ using the configured parameters.
        
        Raises:
            IBMMQConnectionError: If connection to IBM MQ fails
        """
        self._connect()

    async def stop(self) -> None:
        """Stop the IBM MQ client and release all resources.
        
        This method signals any polling operations to stop and closes the connection
        to IBM MQ, ensuring proper cleanup of resources.
        """
        if self.is_polling:
            self.stop_event.set()
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
            }

            if sco is not None:
                connect_params["sco"] = sco

            self.queue_manager.connect_with_options(**connect_params)

        except pymqi.MQMIError as e:
            error_msg = get_error_message(e.reason)
            self.logger.exception(f"Error connecting to queue manager: {error_msg} (Reason: {e.reason})")
            self.last_error = e
            raise IBMMQConnectionError(
                f"Error connecting to queue manager: {error_msg}"
            )
        except Exception as e:
            self.logger.exception(f"Unexpected error connecting to queue manager: {str(e)}")
            self.last_error = e
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
            self.logger.error(f"Error connecting to queue: {error_msg} (Reason: {e.reason})")
            self.last_error = e
            # Close queue manager if already connected
            if self.queue_manager:
                try:
                    self.queue_manager.disconnect()
                except:
                    pass
            raise IBMMQConnectionError(f"Error connecting to queue: {error_msg}")
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to queue: {str(e)}")
            self.last_error = e
            # Close queue manager if already connected
            if self.queue_manager:
                try:
                    self.queue_manager.disconnect()
                except:
                    pass
            raise IBMMQConnectionError(f"Unexpected error connecting to queue: {str(e)}")
            
        self.is_connected = True
        self.reconnect_attempts = 0  # Reset reconnect attempts on successful connection
        self.logger.info("Connected to IBM MQ")

    def _disconnect(self) -> None:
        """Disconnect from the IBM MQ server and clean up resources.
        
        This method closes the queue and disconnects from the queue manager,
        ensuring that resources are properly released regardless of errors.
        """
        try:
            if not self.is_connected:
                return
            if hasattr(self, 'queue') and self.queue:
                self.queue.close()
                self.queue = None
            if hasattr(self, 'queue_manager') and self.queue_manager:
                self.queue_manager.disconnect()
                self.queue_manager = None
            self.is_connected = False
        except Exception as e:
            self.logger.error(
                f"Error disconnecting from queue and queue manager: {str(e)}"
            )
            self.last_error = e
        finally:
            self.is_connected = False
            self.logger.info("Disconnected from IBM MQ")

    async def _reconnect(self) -> bool:
        """Attempt to reconnect to IBM MQ with the configured delay.
        
        This method implements the reconnection logic with a configurable delay
        between attempts. It tracks the number of reconnection attempts and
        can be limited by the max_reconnect_attempts setting.
        
        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        if self.max_reconnect_attempts > 0 and self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error(f"Maximum reconnection attempts ({self.max_reconnect_attempts}) reached. Giving up.")
            self.stop_event.set()
            return False

        # Get delay from config
        delay: int = self.config.reconnect_delay
        
        self.reconnect_attempts += 1
        self.logger.info(f"Attempting to reconnect (attempt {self.reconnect_attempts}) in {delay} second(s)...")
        
        await asyncio.sleep(delay)
        
        try:
            self._connect()
            self.logger.info("Successfully reconnected to IBM MQ")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reconnect: {str(e)}")
            self.last_error = e
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

    async def poll(self, callback: Callable[[bytes], Coroutine[Any, Any, None]]) -> Task:
        """Start polling for messages from the IBM MQ queue.
        
        This method initiates an asynchronous polling loop that continuously
        checks for new messages on the configured queue. When a message is
        received, it processes it and passes it to the provided callback
        function. If the connection is broken, it automatically attempts
        to reconnect.
        
        Args:
            callback: Asynchronous function to call with received messages
            
        Returns:
            asyncio.Task: The polling task that was created
            
        Raises:
            IBMMQConnectionError: If not connected to IBM MQ or for invalid configurations
        """
        if not self.is_connected:
            self.logger.error("Not connected to IBM MQ")
            raise IBMMQConnectionError("Not connected to IBM MQ")
        if callback is None:
            self.logger.error("Callback function not provided")
            # raise ValueError("Callback function not provided")

        async def _process() -> None:
            """Internal processing function that handles message polling.
            
            This function implements the main polling loop which:
            - Checks for and handles disconnections by attempting to reconnect
            - Polls for messages using the configured receiver mode
            - Processes received messages and passes them to the callback
            - Handles various error conditions that may occur during polling
            """
            self.is_polling = True
            connection_broken: bool = False
            
            # Get the appropriate receiver strategy based on the configuration
            try:
                receiver_strategy = get_receiver_strategy(self.config.receiver_mode)
            except ValueError as e:
                self.logger.error(str(e))
                raise IBMMQConnectionError(str(e))
            
            while not self.stop_event.is_set():
                if not self.is_connected or connection_broken:
                    reconnected = await self._reconnect()
                    if not reconnected:
                        # If reconnection failed, continue to next iteration and try again
                        continue
                    connection_broken = False
                    
                try:
                    md: pymqi.MD = pymqi.MD()
                    gmo: pymqi.GMO = pymqi.GMO()
                    gmo.Options = pymqi.CMQC.MQGMO_WAIT | pymqi.CMQC.MQGMO_FAIL_IF_QUIESCING
                    gmo.WaitInterval = self.config.poll_interval_ms

                    if not hasattr(self, 'poll_log_shown'):
                        self.logger.info(
                            f"Polling for messages every {self.config.poll_interval_ms}ms"
                        )
                        setattr(self, 'poll_log_shown', True)
                        
                    try:
                        # Use the strategy to receive a message
                        message = await receiver_strategy.receive_message(self.queue, md, gmo)
                        
                        # Process the message
                        cleaned_message: bytes = self.extract_xml_payload(message)
                        if self.config.log_received_messages:
                            self.logger.info(
                                f"Received Message:\n{gmo.__str__()}\n{md.__str__()}\nMessage:{cleaned_message}"
                            )
                        try:
                            self.logger.info("Received message, calling kubemq target")
                            await callback(cleaned_message)
                            self.messages_received += 1
                            self.logger.info("Messaged processed successfully")
                        except Exception as callback_error:
                            self.logger.error(
                                f"Error in sending to kubemq target: {str(callback_error)}"
                            )
                            self.message_receive_errors += 1
                            self.last_error = callback_error
                        
                        # Reset message descriptors for next get
                        md.MsgId = pymqi.CMQC.MQMI_NONE
                        md.CorrelId = pymqi.CMQC.MQCI_NONE
                        md.GroupId = pymqi.CMQC.MQGI_NONE

                    except pymqi.MQMIError as e:
                        error_type = classify_error(e.reason)
                        error_msg = get_error_message(e.reason)
                        retry_rec = get_retry_recommendation(e.reason)
                        
                        if error_type == ErrorType.TRANSIENT:
                            # For transient errors, just wait and retry
                            if e.reason != pymqi.CMQC.MQRC_NO_MSG_AVAILABLE:  # Don't log no message available
                                self.logger.debug(f"Transient error: {error_msg} (Reason: {e.reason})")
                            await asyncio.sleep(0.1)
                        
                        elif error_type == ErrorType.CONNECTION:
                            # For connection errors, trigger a reconnection
                            self.logger.warning(f"Connection error: {error_msg} (Reason: {e.reason}). Will attempt to reconnect.")
                            connection_broken = True
                            self.is_connected = False
                            self.last_error = e
                        
                        elif error_type == ErrorType.SHUTDOWN:
                            # For shutdown errors, wait longer before reconnecting
                            self.logger.warning(f"Queue manager shutting down: {error_msg} (Reason: {e.reason}). Will attempt to reconnect after delay.")
                            connection_broken = True
                            self.is_connected = False
                            self.last_error = e
                            await asyncio.sleep(retry_rec["retry_delay"])
                        
                        else:
                            # For permanent or configuration errors, log error but keep trying
                            self.logger.error(f"Error polling for message: {error_msg} (Reason: {e.reason})")
                            self.message_receive_errors += 1
                            self.last_error = e
                            await asyncio.sleep(1.0)  # Slightly longer delay for permanent errors
                            
                    except Exception as e:
                        self.logger.error(f"Unexpected error polling for message: {str(e)}")
                        self.message_receive_errors += 1
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
                    await asyncio.sleep(1.0)  # Add delay to avoid spinning in case of repeated errors

            self.is_polling = False
            self.logger.info("Polling stopped")

        self.polling_task = asyncio.create_task(_process())
        return self.polling_task

    async def send_message(self, message: bytes) -> None:
        """Send a message to the IBM MQ queue.
        
        This method sends a message to the configured IBM MQ queue using the
        specified sender mode. If the connection is broken during the send,
        it attempts to reconnect and retry the send operation.
        
        Args:
            message (bytes): The message content to send to the queue
            
        Raises:
            IBMMQConnectionError: If not connected to IBM MQ, the connection breaks,
                                 or for any other error during message sending
        """
        if not self.is_connected:
            self.logger.error("Not connected to IBM MQ")
            raise IBMMQConnectionError("Not connected to IBM MQ")

        message_str: str = message.decode("utf-8")
        if self.config.log_sent_messages:
            self.logger.info(f"Sending message: {message_str}")

        async def _send_message() -> None:
            """Internal function that handles the actual message sending.
            
            This function implements the sending logic which:
            - Determines the appropriate sending method based on the configured sender mode
            - Handles connection errors with reconnection attempts
            - Logs the result of the send operation
            """
            try:
                # Get the appropriate sender strategy based on the configuration
                try:
                    sender_strategy = get_sender_strategy(self.config.sender_mode)
                except ValueError as e:
                    self.logger.error(str(e))
                    raise IBMMQConnectionError(str(e))
                
                # Use the strategy to send the message
                self.logger.info("Sending message to IBM MQ")
                await sender_strategy.send_message(self.queue, message_str, self.config)
                self.messages_sent += 1
                self.logger.info("Message sent successfully")
                
            except pymqi.MQMIError as e:
                error_type = classify_error(e.reason)
                error_msg = get_error_message(e.reason)
                retry_rec = get_retry_recommendation(e.reason)
                self.last_error = e
                
                if error_type == ErrorType.CONNECTION or error_type == ErrorType.SHUTDOWN:
                    self.logger.warning(f"Connection error while sending message: {error_msg} (Reason: {e.reason}). Will attempt to reconnect.")
                    self.is_connected = False
                    
                    # Try to reconnect and send the message again
                    reconnected = await self._reconnect()
                    if reconnected:
                        # Try sending the message again after reconnection
                        await self.send_message(message)
                    else:
                        self.message_send_errors += 1
                        self.logger.error("Failed to reconnect and send message")
                        raise IBMMQConnectionError(f"Error sending message after reconnection attempt: {error_msg}")
                
                elif error_type == ErrorType.TRANSIENT:
                    # For transient errors like queue full, we could implement a retry with backoff
                    self.logger.warning(f"Transient error while sending message: {error_msg} (Reason: {e.reason}). Retrying...")
                    
                    # Implement simple retry for transient errors
                    for retry in range(3):
                        try:
                            await asyncio.sleep(0.5 * (retry + 1))  # Increasing delay
                            await sender_strategy.send_message(self.queue, message_str, self.config)
                            self.messages_sent += 1
                            self.logger.info(f"Message sent successfully after retry {retry+1}")
                            return
                        except pymqi.MQMIError as retry_error:
                            # If we get a non-transient error during retry, raise it
                            if classify_error(retry_error.reason) != ErrorType.TRANSIENT:
                                error_msg = get_error_message(retry_error.reason)
                                self.logger.error(f"Error sending message during retry: {error_msg} (Reason: {retry_error.reason})")
                                self.message_send_errors += 1
                                self.last_error = retry_error
                                raise IBMMQConnectionError(f"Error sending message: {error_msg}")
                    
                    # If we've exhausted retries
                    self.message_send_errors += 1
                    self.logger.error(f"Failed to send message after retries: {error_msg}")
                    raise IBMMQConnectionError(f"Failed to send message after retries: {error_msg}")
                
                else:
                    # For permanent or configuration errors
                    self.message_send_errors += 1
                    self.logger.error(f"Error sending message: {error_msg} (Reason: {e.reason})")
                    raise IBMMQConnectionError(f"Error sending message: {error_msg}")
                
            except Exception as e:
                self.message_send_errors += 1
                self.last_error = e
                self.logger.error(f"Unexpected error sending message: {str(e)}")
                raise IBMMQConnectionError(f"Unexpected error sending message: {str(e)}")

        asyncio.create_task(_send_message())

    async def check_health(self, detailed: bool = False) -> Dict[str, Any]:
        """Check the health of the IBM MQ connection.
        
        This method performs a health check of the IBM MQ connection,
        including checking the queue manager and queue if requested.
        
        Args:
            detailed: Whether to perform detailed checks
            
        Returns:
            Dict containing health status information
        """
        # Cache health check results for 5 seconds to avoid excessive checks
        current_time = asyncio.get_event_loop().time()
        if self.last_health_check is not None and current_time - self.last_health_check_time < 5:
            return self.last_health_check.to_dict()
            
        health_result = await perform_health_check(
            is_connected=self.is_connected,
            queue_manager=self.queue_manager,
            queue=self.queue,
            last_error=self.last_error,
            reconnect_attempts=self.reconnect_attempts,
            max_reconnect_attempts=self.max_reconnect_attempts,
            detailed=detailed
        )
        
        # Add metrics
        health_result.metrics.update({
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "message_send_errors": self.message_send_errors,
            "message_receive_errors": self.message_receive_errors,
            "is_polling": self.is_polling
        })
        
        # Add connection details
        if self.is_connected:
            health_result.details.update({
                "queue_name": self.config.queue_name,
                "queue_manager": self.config.queue_manager,
                "host": self.config.host_name,
                "port": self.config.port_number
            })
        
        # Cache the health check result
        self.last_health_check = health_result
        self.last_health_check_time = current_time
        
        return health_result.to_dict()
