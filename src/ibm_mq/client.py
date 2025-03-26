import asyncio
from asyncio import Event, Task
from typing import Optional, Callable, Any, Coroutine, Union, Dict
import time
import random

from src.bindings.connection import Connection
from src.bindings.metrics import (
    MetricsCollector,
    ConnectionState,
    ErrorCategory
)

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
        health_check_task: Asyncio task for periodic health check
        health_check_interval: Interval between health checks in seconds
        heartbeat_task: Asyncio task for periodic heartbeat
        heartbeat_interval: Interval between heartbeats in seconds
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
        
        # Initialize metrics
        connection_info = {
            "queue_name": self.config.queue_name,
            "queue_manager": self.config.queue_manager,
            "host": self.config.host_name,
            "port": str(self.config.port_number)
        }
        self.metrics = MetricsCollector(
            client_id=self.config.binding_name,
            binding_type="ibm_mq",
            connection_info=connection_info
        )
        
        # Health tracking data
        self.last_error: Optional[Exception] = None
        self.last_health_check: Optional[HealthCheckResult] = None
        self.last_health_check_time: float = 0
        self.health_check_task: Optional[Task] = None
        self.health_check_interval: int = 30  # Check health every 30 seconds
        
        # Heartbeat for non-poll mode clients
        self.heartbeat_task: Optional[Task] = None
        self.heartbeat_interval: int = 15  # Heartbeat every 15 seconds
        

    async def start(self) -> None:
        """Start the IBM MQ client by establishing a connection to the MQ server.
        
        This method initializes the connection to IBM MQ using the configured parameters.
        It also starts the health check and heartbeat tasks for connection monitoring.
        
        Raises:
            IBMMQConnectionError: If connection to IBM MQ fails
        """
        self.metrics.track_connection_state(ConnectionState.CONNECTING)
        self.metrics.track_connection_attempt()
        self._connect()
        
        # Start the health check task
        self.health_check_task = asyncio.create_task(self._periodic_health_check())
        
        # Start the heartbeat task (especially important for non-poll mode)
        self.heartbeat_task = asyncio.create_task(self._periodic_heartbeat())

    async def stop(self) -> None:
        """Stop the IBM MQ client and release all resources.
        
        This method signals any polling operations to stop and closes the connection
        to IBM MQ, ensuring proper cleanup of resources.
        """
        if self.is_polling:
            self.stop_event.set()
            
        # Cancel the health check task if running
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
                
        # Cancel the heartbeat task if running
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
                
        self._disconnect()
        self.metrics.track_connection_state(ConnectionState.DISCONNECTED)

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
            self.transition_to_disconnected(f"Error connecting to queue manager: {error_msg}")
            raise IBMMQConnectionError(
                f"Error connecting to queue manager: {error_msg}"
            )
        except Exception as e:
            self.logger.exception(f"Unexpected error connecting to queue manager: {str(e)}")
            self.transition_to_disconnected(f"Unexpected error connecting to queue manager: {str(e)}")
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
            self.transition_to_disconnected(f"Unexpected error connecting to queue: {str(e)}")
            # Close queue manager if already connected
            if self.queue_manager:
                try:
                    self.queue_manager.disconnect()
                except:
                    pass
            raise IBMMQConnectionError(f"Unexpected error connecting to queue: {str(e)}")
            
        # Connection successful - transition to connected state
        self.transition_to_connected()
        self.logger.info("Connected to IBM MQ")
        
        # Try to update queue metrics
        try:
            queue_depth = self.queue.inquire(pymqi.CMQC.MQIA_CURRENT_Q_DEPTH)
            max_depth = self.queue.inquire(pymqi.CMQC.MQIA_MAX_Q_DEPTH)
            self.metrics.track_queue_metrics(queue_depth, max_depth)
        except:
            # Non-critical operation, just ignore if it fails
            pass

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
        except Exception as e:
            self.logger.error(
                f"Error disconnecting from queue and queue manager: {str(e)}"
            )
            # Even on disconnect error, we still consider ourselves disconnected
            # but we track the error
            self.metrics.track_error(ErrorCategory.CONNECTION, f"Error disconnecting: {str(e)}")
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
        if self.max_reconnect_attempts > 0 and self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error(f"Maximum reconnection attempts ({self.max_reconnect_attempts}) reached. Giving up.")
            self.stop_event.set()
            return False

        # Use exponential backoff with jitter for retries
        base_delay = self.config.reconnect_delay
        max_delay = min(60, base_delay * (2 ** min(self.reconnect_attempts, 5)))  # Cap at 60 seconds
        delay = base_delay + (random.random() * (max_delay - base_delay))
        
        self.reconnect_attempts += 1
        self.transition_to_reconnecting()
        self.logger.info(f"Attempting to reconnect (attempt {self.reconnect_attempts}) in {delay:.2f} second(s)...")
        
        await asyncio.sleep(delay)
        
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
                        start_time = time.time()
                        
                        # Use the strategy to receive a message
                        message = await receiver_strategy.receive_message(self.queue, md, gmo)
                        
                        # Calculate receive duration
                        receive_duration_ms = (time.time() - start_time) * 1000
                        
                        # Process the message
                        cleaned_message: bytes = self.extract_xml_payload(message)
                        if self.config.log_received_messages:
                            self.logger.info(
                                f"Received Message:\n{gmo.__str__()}\n{md.__str__()}\nMessage:{cleaned_message}"
                            )
                        try:
                            callback_start_time = time.time()
                            self.logger.info("Received message, calling kubemq target")
                            await callback(cleaned_message)
                            callback_duration_ms = (time.time() - callback_start_time) * 1000
                            
                            # Track successful message receive
                            self.metrics.track_message_received(receive_duration_ms)
                            self.logger.info("Messaged processed successfully")
                        except Exception as callback_error:
                            self.logger.error(
                                f"Error in sending to kubemq target: {str(callback_error)}"
                            )
                            self.last_error = callback_error
                            self.metrics.track_error(
                                ErrorCategory.RECEIVE, 
                                f"Error processing received message: {str(callback_error)}"
                            )
                        
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
                            self.metrics.track_error(
                                ErrorCategory.CONNECTION, 
                                f"Connection error while polling: {error_msg}"
                            )
                        
                        elif error_type == ErrorType.SHUTDOWN:
                            # For shutdown errors, wait longer before reconnecting
                            self.logger.warning(f"Queue manager shutting down: {error_msg} (Reason: {e.reason}). Will attempt to reconnect after delay.")
                            connection_broken = True
                            self.is_connected = False
                            self.last_error = e
                            self.metrics.track_error(
                                ErrorCategory.CONNECTION, 
                                f"Queue manager shutting down: {error_msg}"
                            )
                            await asyncio.sleep(retry_rec["retry_delay"])
                        
                        else:
                            # For permanent or configuration errors, log error but keep trying
                            self.logger.error(f"Error polling for message: {error_msg} (Reason: {e.reason})")
                            self.last_error = e
                            self.metrics.track_error(
                                ErrorCategory.RECEIVE, 
                                f"Error polling for message: {error_msg}"
                            )
                            await asyncio.sleep(1.0)  # Slightly longer delay for permanent errors
                            
                    except Exception as e:
                        self.logger.error(f"Unexpected error polling for message: {str(e)}")
                        self.last_error = e
                        self.metrics.track_error(
                            ErrorCategory.UNKNOWN, 
                            f"Unexpected error polling for message: {str(e)}"
                        )
                        # Mark connection as broken for most exceptions to trigger reconnection
                        if self.is_connected:
                            connection_broken = True
                            self.is_connected = False
                except Exception as e:
                    self.logger.error(f"Error in polling loop: {str(e)}")
                    self.last_error = e
                    self.metrics.track_error(
                        ErrorCategory.UNKNOWN, 
                        f"Error in polling loop: {str(e)}"
                    )
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
            self.logger.info("Not connected to IBM MQ, attempting reconnection before sending")
            reconnected = await self._reconnect()
            if not reconnected:
                raise IBMMQConnectionError("Not connected to IBM MQ, reconnection failed")
        
        # Explicitly validate connection before sending
        connection_valid = await self.test_connection_directly()
        if not connection_valid:
            self.logger.warning("Connection validation failed before sending, attempting reconnection")
            self.transition_to_disconnected("Connection validation failed before send operation")
            reconnected = await self._reconnect()
            if not reconnected:
                raise IBMMQConnectionError("Connection validation failed before send operation")

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
                    self.metrics.track_error(
                        ErrorCategory.CONFIGURATION, 
                        f"Invalid sender mode: {str(e)}"
                    )
                    raise IBMMQConnectionError(str(e))
                
                # Use the strategy to send the message
                self.logger.debug("Sending message to IBM MQ")
                start_time = time.time()
                await sender_strategy.send_message(self.queue, message_str, self.config)
                send_duration_ms = (time.time() - start_time) * 1000
                self.metrics.track_message_sent(send_duration_ms)
                self.logger.debug(f"Message sent to IBM MQ in {send_duration_ms:.2f}ms")
                
            except pymqi.MQMIError as e:
                error_msg = get_error_message(e.reason)
                error_type = classify_error(error_msg)
                self.logger.error(f"Error sending message to IBM MQ: {error_msg} (Reason: {e.reason})")
                
                # Track the error
                self.metrics.track_error(ErrorCategory.SEND, f"Error sending message: {error_msg}")
                
                # For connection-related errors, attempt reconnection
                if error_type == ErrorType.CONNECTION or error_type == ErrorType.SHUTDOWN:
                    self.transition_to_disconnected(f"Send failed: {error_msg}")
                    reconnected = await self._reconnect()
                    if reconnected:
                        # Retry the send after reconnection
                        await self.send_message(message)
                        return
                
                raise IBMMQConnectionError(f"Error sending message to IBM MQ: {error_msg}")
            except Exception as e:
                self.logger.error(f"Unexpected error sending message to IBM MQ: {str(e)}")
                self.transition_to_disconnected(f"Unexpected error during send: {str(e)}")
                raise IBMMQConnectionError(f"Unexpected error sending message: {str(e)}")

        await _send_message()

    async def check_health(self) -> Dict[str, Any]:
        """Check the health of the IBM MQ connection.
        
        This method performs a direct health check of the IBM MQ connection
        focusing on connection status. It uses direct connection testing
        to accurately detect connection issues independent of current state.
        
        Returns:
            Dict containing health status information
        """
        # Cache health check results for 5 seconds to avoid excessive checks
        current_time = asyncio.get_event_loop().time()
        if self.last_health_check is not None and current_time - self.last_health_check_time < 5:
            return self.last_health_check.to_dict()
            
        # First, directly test the connection regardless of current state
        connection_active = await self.test_connection_directly()
        
        # Update internal state based on actual connection test results
        if connection_active and not self.is_connected:
            self.transition_to_connected()
        elif not connection_active and self.is_connected:
            self.transition_to_disconnected("Connection test failed during health check")
        
        # Now perform the regular health check
        health_result = await perform_health_check(
            is_connected=self.is_connected,
            queue_manager=self.queue_manager,
            queue=self.queue,
            last_error=self.last_error
        )
        
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
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics for this client.
        
        Returns:
            Dict containing all metrics data
        """
        return self.metrics.get_all_metrics()

    async def _periodic_health_check(self) -> None:
        """Periodic health check task that runs periodically to detect connection issues.
        
        This method performs a health check of the IBM MQ connection at a regular interval.
        If the connection is broken, it attempts to reconnect.
        """
        while not self.stop_event.is_set():
            try:
                await asyncio.sleep(self.health_check_interval)
                
                # Skip health check if we're already trying to reconnect
                if self.is_connected and not self.stop_event.is_set():
                    health_result = await self.check_health()
                    
                    # If connection is unhealthy but we think we're connected, try to reconnect
                    if (health_result["status"] == HealthStatus.UNHEALTHY and 
                            "queue_manager_check" in health_result["errors"] and 
                            self.is_connected):
                        self.logger.warning("Periodic health check detected connection issue. Attempting to reconnect...")
                        # Set connection status to disconnected
                        self.is_connected = False
                        self.metrics.track_connection_state(ConnectionState.DISCONNECTED)
                        # Try to reconnect
                        asyncio.create_task(self._reconnect())
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic health check: {str(e)}")
                await asyncio.sleep(5)  # Wait a bit before retrying on error

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
            self.logger.debug(f"Direct connection test failed: {str(e)}")
            return False

    def transition_to_connected(self) -> None:
        """Transition to connected state.
        
        Centralized method to ensure all state variables are updated consistently
        when transitioning to connected state.
        """
        previous_state = "connected" if self.is_connected else "disconnected"
        self.is_connected = True
        self.last_error = None
        self.reconnect_attempts = 0
        self.metrics.track_connection_state(ConnectionState.CONNECTED)
        self.logger.info(f"State transition: {previous_state} -> connected")
        
        # Reset health check cache to ensure fresh health check
        self.last_health_check = None
        self.last_health_check_time = 0
        
    def transition_to_disconnected(self, reason: str) -> None:
        """Transition to disconnected state.
        
        Centralized method to ensure all state variables are updated consistently
        when transitioning to disconnected state.
        
        Args:
            reason: The reason for disconnection
        """
        if self.is_connected:  # Only log if actually changing state
            self.logger.info(f"State transition: connected -> disconnected (Reason: {reason})")
            
        self.is_connected = False
        self.last_error = Exception(reason)
        self.metrics.track_connection_state(ConnectionState.DISCONNECTED)
        
        # Reset health check cache to ensure fresh health check
        self.last_health_check = None
        self.last_health_check_time = 0
        
    def transition_to_reconnecting(self) -> None:
        """Transition to reconnecting state.
        
        Centralized method to ensure all state variables are updated consistently
        when transitioning to reconnecting state.
        """
        self.is_connected = False
        self.metrics.track_connection_state(ConnectionState.RECONNECTING)
        self.metrics.track_reconnection_attempt()
        self.logger.info(f"State transition: disconnected -> reconnecting (Attempt: {self.reconnect_attempts + 1})")
        
        # Reset health check cache to ensure fresh health check
        self.last_health_check = None
        self.last_health_check_time = 0

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
                    health_result = await self.check_health()
                    
                    # If connection is unhealthy but we think we're connected, try to reconnect
                    if (health_result["status"] == HealthStatus.UNHEALTHY and 
                            "queue_manager_check" in health_result["errors"] and 
                            self.is_connected):
                        self.logger.warning("Periodic heartbeat detected connection issue. Attempting to reconnect...")
                        # Set connection status to disconnected
                        self.is_connected = False
                        self.metrics.track_connection_state(ConnectionState.DISCONNECTED)
                        # Try to reconnect
                        asyncio.create_task(self._reconnect())
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic heartbeat: {str(e)}")
                await asyncio.sleep(5)  # Wait a bit before retrying on error
