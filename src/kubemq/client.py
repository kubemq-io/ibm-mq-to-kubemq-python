import asyncio
import os
import time
from asyncio import Event, Task
from enum import Enum
from typing import Dict, Any, Optional, Set, List

from kubemq.queues import Client, QueueMessage, ReceiveQueueMessagesRequest

from src.bindings.connection import Connection
from src.bindings.metrics import MetricsCollector, ConnectionState, ErrorCategory
from src.kubemq.exceptions import KubeMQConnectionError

# Remove unrelated IBM MQ environment variable
# os.environ.setdefault("MQ_FILE_PATH", "C:/Program Files (x86)/IBM/WebSphere MQ")

from src.common.log import get_logger
from src.kubemq.config import Config


class ErrorType(Enum):
    """Types of errors that can occur in KubeMQ operations.

    This classification helps determine the appropriate handling strategy
    for different types of errors.
    """

    TRANSIENT = "transient"  # Temporary errors that may resolve on retry
    CONNECTION = "connection"  # Connection-related errors
    CONFIGURATION = "configuration"  # Configuration/setup errors
    PERMANENT = "permanent"  # Errors that won't be resolved by retrying


def classify_error(error_msg: str) -> ErrorType:
    """Classify an error based on its message to determine handling strategy.

    Args:
        error_msg: The error message to classify

    Returns:
        ErrorType: The classified error type
    """
    error_msg = error_msg.lower()

    # Connection-related errors
    if any(
        term in error_msg
        for term in ["connection", "connect", "network", "unreachable"]
    ):
        return ErrorType.CONNECTION

    # Temporary/transient errors
    if any(
        term in error_msg
        for term in ["timeout", "unavailable", "temporary", "overload"]
    ):
        return ErrorType.TRANSIENT

    # Configuration errors
    if any(term in error_msg for term in ["config", "invalid", "permission", "auth"]):
        return ErrorType.CONFIGURATION

    # Default to permanent error
    return ErrorType.PERMANENT


class KubeMQClient(Connection):
    """KubeMQ client for interacting with KubeMQ messaging services.

    This class handles the complete lifecycle of KubeMQ connections including
    establishing connections, sending and receiving messages, and monitoring
    health and metrics.

    Attributes:
        config: Configuration for the KubeMQ connection
        logger: Logger instance for this client
        client: KubeMQ client instance
        is_polling: Flag indicating if client is actively polling
        should_stop_polling: Flag indicating if client should stop polling
        stop_event: Event used to signal stopping of background tasks
        is_connected: Flag indicating connection status
        polling_task: Task handling the message polling
        last_error: Last error encountered by the client
        metrics: Metrics collector for monitoring
        _tasks: Set of created async tasks for management
    """

    def __init__(self, config: Config):
        """Initialize the KubeMQ client with the provided configuration.

        Args:
            config: Configuration object containing KubeMQ connection parameters
        """
        self.config: Config = config
        self.logger = get_logger(
            f"kubemq.{self.config.binding_name}.{self.config.binding_type}"
        )
        self.client: Client | None = None
        self.is_polling = False
        self.should_stop_polling = False
        self.stop_event: Event = Event()
        self.is_connected = False
        self.polling_task: Optional[Task] = None
        self.last_error: Optional[Exception] = None
        self._tasks: Set[Task] = set()  # Track all created tasks for proper cleanup

        # Initialize metrics
        connection_info = {
            "queue_name": self.config.queue_name,
            "address": self.config.address,
            "client_id": self.config.client_id,
        }
        self.metrics = MetricsCollector(
            client_id=self.config.binding_name,
            binding_type="kubemq",
            connection_info=connection_info,
        )

    def _create_tracked_task(self, coro) -> Task:
        """Create and track an asyncio task.

        This helper method ensures all created tasks are properly tracked
        for cleanup during shutdown.

        Args:
            coro: The coroutine to schedule

        Returns:
            Task: The created task
        """
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)  # Auto-remove when done
        return task

    async def start(self):
        """Start the KubeMQ client by establishing a connection to the server.

        This method initializes the connection to KubeMQ using the configured
        parameters and prepares the client for sending and receiving messages.

        Raises:
            KubeMQConnectionError: If connection to KubeMQ fails
        """
        self.metrics.track_connection_state(ConnectionState.CONNECTING)
        self.metrics.track_connection_attempt()
        self._connect()

    async def stop(self):
        """Stop the KubeMQ client and release all resources.

        This method:
        1. Signals polling operations to stop
        2. Cancels any pending background tasks
        3. Disconnects from the KubeMQ server
        4. Updates the connection state

        All tasks are properly cancelled and awaited to ensure clean shutdown.
        """
        if self.is_polling:
            self.should_stop_polling = True
            self.stop_event.set()

        # Cancel all pending tasks
        pending_tasks = [t for t in self._tasks if not t.done()]
        if pending_tasks:
            self.logger.debug(f"Cancelling {len(pending_tasks)} pending tasks")
            for task in pending_tasks:
                task.cancel()

            # Wait for all tasks to complete cancellation
            if pending_tasks:
                await asyncio.gather(*pending_tasks, return_exceptions=True)

        self._tasks.clear()
        self._disconnect()
        self.metrics.track_connection_state(ConnectionState.DISCONNECTED)

    def _connect(self):
        """Establish a connection to the KubeMQ server.

        This method initializes the KubeMQ client using the configured parameters.
        If the connection fails, appropriate error handling is performed including
        logging, metrics tracking, and error classification.

        Raises:
            KubeMQConnectionError: If connection to KubeMQ fails
        """
        try:
            self.client = Client(
                address=self.config.address,
                client_id=self.config.client_id,
            )
        except Exception as e:
            error_msg = str(e)
            error_type = classify_error(error_msg)
            self.logger.error(
                f"Error connecting to KubeMQ server: {error_msg} (Type: {error_type.value})"
            )
            self.last_error = e
            self.metrics.track_error(
                ErrorCategory.CONNECTION,
                f"Error connecting to KubeMQ server: {error_msg}",
            )
            raise KubeMQConnectionError(
                f"Error connecting to KubeMQ server: {error_msg} (Type: {error_type.value})"
            )
        self.is_connected = True
        # Clear last_error when connection is successful
        self.last_error = None
        self.metrics.track_connection_state(ConnectionState.CONNECTED)
        self.logger.info("Connected to KubeMQ")

    def _disconnect(self):
        """Disconnect from the KubeMQ server and clean up resources.

        This method handles the disconnection process, ensuring all resources
        are properly released and the connection state is updated.

        Note: The KubeMQ Python client currently doesn't have an explicit close method.
        This method primarily updates the connection state and logs the disconnection.
        """
        try:
            if not self.is_connected:
                return
            # No explicit close method currently available in the KubeMQ Python client
            # If one becomes available in the future, it should be called here
        except Exception as e:
            error_msg = str(e)
            error_type = classify_error(error_msg)
            self.logger.exception(
                f"Error disconnecting from KubeMQ server: {error_msg} (Type: {error_type.value})"
            )
            self.last_error = e
            self.metrics.track_error(
                ErrorCategory.CONNECTION,
                f"Error disconnecting from KubeMQ server: {error_msg}",
            )
            raise KubeMQConnectionError(
                f"Error disconnecting from KubeMQ server: {error_msg} (Type: {error_type.value})"
            )
        finally:
            self.is_connected = False
            self.metrics.track_connection_state(ConnectionState.DISCONNECTED)
            self.logger.info("Disconnected from KubeMQ")

    async def poll(self, callback):
        """Start polling for messages from the KubeMQ queue.
        
        This method initiates an asynchronous polling loop that continuously
        checks for new messages on the configured queue. When messages are
        received, they are processed and passed to the provided callback function.
        
        The polling process includes:
        1. Waiting for messages with a configured timeout
        2. Processing received messages
        3. Calling the provided callback function with message content
        4. Acknowledging or rejecting messages based on processing success
        5. Handling errors with appropriate classification and metrics
        
        Args:
            callback: Asynchronous function to call with received messages
            
        Returns:
            asyncio.Task: The polling task that was created
            
        Raises:
            KubeMQConnectionError: If not connected to KubeMQ
        """
        if not self.is_connected:
            self.logger.error("Not connected to KubeMQ")
            raise KubeMQConnectionError("Not connected to KubeMQ")
        if callback is None:
            self.logger.error("Callback function not provided")
            raise ValueError("Callback function not provided")
        
        async def _process():
            """Internal processing function for message polling.
            
            This function handles the main polling loop, including:
            - Fetching messages from the KubeMQ queue
            - Processing messages and calling the callback
            - Error handling with appropriate recovery
            - Metrics collection and monitoring
            """
            self.is_polling = True
            self.logger.info(f"Starting to poll for messages from {self.config.queue_name}")
            
            while self.is_polling and not self.should_stop_polling and not self.stop_event.is_set():
                try:
                    poll_start_time = time.time()
                    poll_response = await asyncio.to_thread(
                        self.client.receive_queues_messages,
                        channel=self.config.queue_name,
                        max_messages=1,
                        wait_timeout_in_seconds=self.config.poll_interval_seconds,
                    )
                    poll_duration_ms = (time.time() - poll_start_time) * 1000
                    
                    if poll_response.is_error:
                        error_msg = poll_response.error
                        error_type = classify_error(error_msg)
                        self.logger.error(
                            f"Error polling messages: {error_msg} (Type: {error_type.value})"
                        )
                        self.last_error = Exception(error_msg)
                        self.metrics.track_error(
                            ErrorCategory.RECEIVE, 
                            f"Error polling messages: {error_msg}",
                            is_send=False
                        )
                        
                        # Apply different wait strategies based on error type
                        if error_type == ErrorType.TRANSIENT:
                            await asyncio.sleep(self.config.poll_interval_seconds / 2)
                        elif error_type == ErrorType.CONNECTION:
                            await asyncio.sleep(self.config.poll_interval_seconds * 2)
                        else:
                            await asyncio.sleep(self.config.poll_interval_seconds)
                        continue
                        
                    if len(poll_response.messages) == 0:
                        continue

                    for message in poll_response.messages:
                        try:
                            self.logger.info(f"Received message: {message.body}")
                            callback_start_time = time.time()
                            await callback(message.body)
                            callback_duration_ms = (time.time() - callback_start_time) * 1000
                            
                            # Track successful message receive with size
                            message_size = len(message.body) if message.body is not None else 0
                            self.metrics.track_message_received(message_size)
                            is_message_processed = True
                        except Exception as callback_error:
                            error_msg = str(callback_error)
                            error_type = classify_error(error_msg)
                            self.logger.error(
                                f"Error in callback function: {error_msg} (Type: {error_type.value}), rejecting message"
                            )
                            self.last_error = callback_error
                            self.metrics.track_error(
                                ErrorCategory.RECEIVE, 
                                f"Error processing received message: {error_msg}",
                                is_send=False
                            )
                            is_message_processed = False

                        try:
                            ack_start_time = time.time()
                            if is_message_processed:
                                message.ack()
                            else:
                                message.reject()
                            ack_duration_ms = (time.time() - ack_start_time) * 1000
                        except Exception as e:
                            error_msg = str(e)
                            error_type = classify_error(error_msg)
                            self.logger.error(
                                f"Error acknowledging/rejecting message: {error_msg} (Type: {error_type.value})"
                            )
                            self.last_error = e
                            self.metrics.track_error(
                                ErrorCategory.RECEIVE, 
                                f"Error acknowledging/rejecting message: {error_msg}",
                                is_send=False
                            )
                            
                            # Apply different wait strategies based on error type
                            if error_type == ErrorType.TRANSIENT:
                                await asyncio.sleep(self.config.poll_interval_seconds / 2)
                            else:
                                await asyncio.sleep(self.config.poll_interval_seconds)

                except Exception as e:
                    error_msg = str(e)
                    error_type = classify_error(error_msg)
                    self.logger.error(f"Error processing message: {error_msg} (Type: {error_type.value})")
                    self.last_error = e
                    self.metrics.track_error(
                        ErrorCategory.UNKNOWN, 
                        f"Error in polling loop: {error_msg}",
                        is_send=False
                    )
                    
                    # Apply different wait strategies based on error type
                    if error_type == ErrorType.TRANSIENT:
                        await asyncio.sleep(self.config.poll_interval_seconds / 2)
                    elif error_type == ErrorType.CONNECTION:
                        await asyncio.sleep(self.config.poll_interval_seconds * 2)
                    else:
                        await asyncio.sleep(self.config.poll_interval_seconds)
            
            self.is_polling = False
            self.logger.info("Polling stopped")

        self.polling_task = self._create_tracked_task(_process())
        return self.polling_task

    async def send_message(self, message: bytes):
        """Send a message to the KubeMQ queue.

        This method sends a message to the configured KubeMQ queue. The operation
        is performed asynchronously with proper error handling and metrics tracking.

        The sending process includes:
        1. Validating connection status
        2. Sending the message to the KubeMQ queue
        3. Tracking send performance metrics
        4. Handling and classifying any errors that occur

        Args:
            message: The message content to send to the queue

        Raises:
            KubeMQConnectionError: If not connected to KubeMQ
        """
        if not self.is_connected:
            self.logger.error("Not connected to KubeMQ")
            raise KubeMQConnectionError("Not connected to KubeMQ")

        async def _send_message():
            """Internal function that handles the actual message sending.

            This function implements the sending logic including:
            - Sending the message to the configured queue
            - Performance metrics tracking
            - Error handling with classification
            - Logging the result of the operation
            """
            try:
                self.logger.info("Sending message to KubeMQ")
                start_time = time.time()
                result = await asyncio.to_thread(
                    self.client.send_queues_message,
                    QueueMessage(
                        body=message,
                        channel=self.config.queue_name,
                    ),
                )
                send_duration_ms = (time.time() - start_time) * 1000

                # Track successful send with message size
                self.metrics.track_message_sent(len(message))

                self.logger.info("Message sent to KubeMQ")
                if result.is_error:
                    error_msg = result.error
                    error_type = classify_error(error_msg)
                    self.logger.error(
                        f"Error sending message: {error_msg} (Type: {error_type.value})"
                    )
                    self.last_error = Exception(error_msg)
                    self.metrics.track_error(
                        ErrorCategory.SEND,
                        f"Error sending message: {error_msg}",
                        is_send=True,
                    )
            except Exception as e:
                error_msg = str(e)
                error_type = classify_error(error_msg)
                self.logger.error(
                    f"Error sending message: {error_msg} (Type: {error_type.value})"
                )
                self.last_error = e
                self.metrics.track_error(
                    ErrorCategory.UNKNOWN,
                    f"Unexpected error sending message: {error_msg}",
                    is_send=True,
                )

        self._create_tracked_task(_send_message())

    async def check_health(self) -> Dict[str, Any]:
        """Check the health of the KubeMQ connection.

        This method performs a comprehensive health check of the KubeMQ connection,
        including:
        - Connection state verification
        - Server ping to verify actual connectivity
        - Error state checking
        - Latency measurement

        Returns:
            Dict containing health status and details
        """
        health_result = {
            "status": "healthy",
            "details": {
                "connection_status": "disconnected",
                "address": self.config.address,
                "queue_name": self.config.queue_name,
                "client_id": self.config.client_id,
            },
            "errors": {},
        }

        # Add error details if we have a last error
        if self.last_error is not None:
            error_msg = str(self.last_error)
            error_type = classify_error(error_msg)
            health_result["errors"][
                "last_error"
            ] = f"{error_msg} (Type: {error_type.value})"
            health_result["status"] = "unhealthy"

        # If connected, try to ping the server to verify actual connectivity
        if self.is_connected:
            try:
                ping_start_time = time.time()
                ping_result = self.client.ping()
                ping_duration_ms = (time.time() - ping_start_time) * 1000

                # If ping successful, clear last_error and ensure connection is marked as connected
                self.last_error = None
                self.is_connected = True
                self.metrics.track_connection_state(ConnectionState.CONNECTED)

                # Update health status and connection status
                health_result["status"] = "healthy"
                health_result["details"]["connection_status"] = "connected"

                # Format the ping latency to have at most 2 decimal places
                health_result["details"]["latency_msec"] = (
                    round(ping_duration_ms * 100) / 100
                )
            except Exception as e:
                error_msg = str(e)
                error_type = classify_error(error_msg)

                # Update connection status to disconnected and set last_error
                self.is_connected = False
                self.last_error = e
                self.metrics.track_connection_state(ConnectionState.DISCONNECTED)

                health_result["status"] = "unhealthy"
                health_result["details"]["connection_status"] = "disconnected"
                health_result["errors"][
                    "connectivity_check"
                ] = f"{error_msg} (Type: {error_type.value})"

        return health_result

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics for this connection.

        This method returns a comprehensive set of metrics about the KubeMQ connection
        and its operations, including performance, state, errors, and operational counters.

        The metrics provide visibility into:
        - Message throughput (sent/received)
        - Operation latencies
        - Error counts and categories
        - Connection states and uptime
        - System resource utilization

        Returns:
            Dict containing all metrics data collected for this connection
        """
        # Get all metrics from the metrics collector
        all_metrics = self.metrics.get_all_metrics()

        try:
            ping_start_time = time.time()
            self.client.ping()
            ping_duration_ms = (time.time() - ping_start_time) * 1000

            # If ping successful, clear last_error and ensure connection is marked as connected
            self.last_error = None
            self.is_connected = True

            # Add latency metric with at most 2 decimal places
            if "state" not in all_metrics:
                all_metrics["state"] = {}
            all_metrics["state"]["latency_msec"] = round(ping_duration_ms * 100) / 100
        except Exception as e:
            # Update connection status to disconnected and set last_error
            self.is_connected = False
            self.last_error = e
            self.metrics.track_connection_state(ConnectionState.DISCONNECTED)

        return all_metrics

    def transition_to_reconnecting(self) -> None:
        """Transition the client to reconnecting state."""
        self.is_connected = False
        self.metrics.track_connection_state(ConnectionState.CONNECTING)
        self.logger.info("Transitioning to reconnecting state")

    async def _reconnect(self) -> bool:
        """Attempt to reconnect to the KubeMQ server.
        
        This method handles the reconnection process with proper state transitions
        and error handling. It will attempt to establish a new connection and
        update the client's state accordingly.
        
        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        try:
            self.transition_to_reconnecting()
            
            # Create new client instance
            self.client = Client(
                address=self.config.address,
                client_id=self.config.client_id,
                auth_token=self.config.auth_token,
                use_tls=self.config.use_tls,
                cert_file=self.config.cert_file,
                key_file=self.config.key_file,
                skip_verify=self.config.skip_verify,
            )
            
            # Test connection with ping
            self.client.ping()
            
            # Update state to connected
            self.is_connected = True
            self.metrics.track_connection_state(ConnectionState.CONNECTED)
            self.last_error = None
            self.logger.info("Successfully reconnected to KubeMQ server")
            return True
            
        except Exception as e:
            error_msg = str(e)
            error_type = classify_error(error_msg)
            self.logger.error(f"Failed to reconnect to KubeMQ server: {error_msg}")
            self.last_error = e
            self.metrics.track_connection_state(ConnectionState.DISCONNECTED)
            return False
