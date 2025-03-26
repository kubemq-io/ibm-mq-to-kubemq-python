"""Metrics collection for messaging bindings.

This module provides a comprehensive metrics collection system for messaging operations,
allowing tracking of operational performance, errors, and status for various binding types.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any


class ConnectionState(Enum):
    """Possible connection states for tracking metrics."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    RECONNECTING = "reconnecting"


class ErrorCategory(Enum):
    """Categories of errors for metrics tracking."""
    CONNECTION = "connection"
    SEND = "send"
    RECEIVE = "receive"
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class HistogramMetric:
    """Histogram metric for tracking value distributions."""
    name: str
    description: str
    values: List[float] = field(default_factory=list)
    count: int = 0
    sum: float = 0
    # Track percentiles: p50, p95, p99
    percentiles: Dict[str, float] = field(default_factory=dict)
    
    def add_value(self, value: float) -> None:
        """Add a value to the histogram.
        
        Args:
            value: The value to add
        """
        self.values.append(value)
        self.count += 1
        self.sum += value
        # Only recalculate percentiles after collecting enough samples
        if self.count % 10 == 0 and self.values:
            self._update_percentiles()
    
    def _update_percentiles(self) -> None:
        """Update the percentile calculations."""
        sorted_values = sorted(self.values)
        self.percentiles["p50"] = sorted_values[int(0.5 * len(sorted_values))]
        self.percentiles["p95"] = sorted_values[int(0.95 * len(sorted_values))]
        self.percentiles["p99"] = sorted_values[int(0.99 * len(sorted_values))]
    
    def reset(self) -> None:
        """Reset the histogram values while maintaining metadata."""
        self.values = []
        self.count = 0
        self.sum = 0
        self.percentiles = {}


@dataclass
class CounterMetric:
    """Counter metric for tracking cumulative values."""
    name: str
    description: str
    value: int = 0
    
    def increment(self, amount: int = 1) -> None:
        """Increment the counter.
        
        Args:
            amount: The amount to increment by
        """
        self.value += amount


@dataclass
class GaugeMetric:
    """Gauge metric for tracking current state values."""
    name: str
    description: str
    value: Union[float, int, str] = 0
    
    def set(self, value: Union[float, int, str]) -> None:
        """Set the gauge value.
        
        Args:
            value: The value to set
        """
        self.value = value


class MetricsCollector:
    """Collector for messaging client metrics.
    
    This class provides a centralized metrics collection system that can be
    used by messaging clients to track performance, errors, and operational status.
    """
    
    def __init__(self, client_id: str, binding_type: str, connection_info: Dict[str, str]):
        """Initialize the metrics collector.
        
        Args:
            client_id: Identifier for the client
            binding_type: Type of binding (e.g. "ibm_mq", "kubemq")
            connection_info: Dictionary of connection details for labeling metrics
        """
        self.client_id = client_id
        self.binding_type = binding_type
        self.connection_info = connection_info
        self.start_time = time.time()
        self.last_connection_time: Optional[float] = None
        
        # Initialize metrics
        self._initialize_metrics()
        
    def _initialize_metrics(self) -> None:
        """Initialize all metrics with default values."""
        # Operational counters
        self.message_sent_total = CounterMetric(
            name="message_sent_total",
            description="Total number of messages sent"
        )
        
        self.message_received_total = CounterMetric(
            name="message_received_total",
            description="Total number of messages received"
        )
        
        self.errors_total = CounterMetric(
            name="errors_total",
            description="Total number of errors"
        )
        
        self.connection_attempts_total = CounterMetric(
            name="connection_attempts_total",
            description="Total connection attempts"
        )
        
        self.reconnection_attempts_total = CounterMetric(
            name="reconnection_attempts_total",
            description="Total reconnection attempts"
        )
        
        # Error metrics by category
        self.errors_by_category: Dict[ErrorCategory, CounterMetric] = {
            category: CounterMetric(
                name=f"errors_{category.value}_total",
                description=f"Total errors of type {category.value}"
            ) for category in ErrorCategory
        }
        
        # Performance metrics
        self.message_send_duration_ms = HistogramMetric(
            name="message_send_duration_ms",
            description="Time taken to send messages in milliseconds"
        )
        
        self.message_receive_duration_ms = HistogramMetric(
            name="message_receive_duration_ms",
            description="Time taken to receive messages in milliseconds"
        )
        
        # State metrics
        self.connection_state = GaugeMetric(
            name="connection_state",
            description="Current connection state (1=connected, 0=disconnected)"
        )
        
        self.queue_depth = GaugeMetric(
            name="queue_depth",
            description="Current queue depth"
        )
        
        self.queue_utilization_percent = GaugeMetric(
            name="queue_utilization_percent",
            description="Queue usage percentage"
        )
        
        # System metrics
        self.uptime_seconds = GaugeMetric(
            name="uptime_seconds",
            description="Time since client started in seconds"
        )
        
        self.connection_uptime_seconds = GaugeMetric(
            name="connection_uptime_seconds",
            description="Time since last successful connection in seconds"
        )
        
        # Initialize additional tracking
        self.last_error_timestamp: Optional[float] = None
        self.last_error_message: Optional[str] = None
    
    def track_connection_attempt(self) -> None:
        """Track a connection attempt."""
        self.connection_attempts_total.increment()
    
    def track_reconnection_attempt(self) -> None:
        """Track a reconnection attempt."""
        self.reconnection_attempts_total.increment()
    
    def track_connection_state(self, state: ConnectionState) -> None:
        """Track connection state changes.
        
        Args:
            state: The new connection state
        """
        if state == ConnectionState.CONNECTED:
            self.connection_state.set(1)
            self.last_connection_time = time.time()
        elif state == ConnectionState.DISCONNECTED:
            self.connection_state.set(0)
        elif state == ConnectionState.CONNECTING:
            self.connection_state.set(0.5)  # Intermediate state
        elif state == ConnectionState.RECONNECTING:
            self.connection_state.set(0.5)  # Intermediate state
    
    def track_message_sent(self, duration_ms: Optional[float] = None) -> None:
        """Track a message being sent.
        
        Args:
            duration_ms: The time taken to send the message in milliseconds
        """
        self.message_sent_total.increment()
        if duration_ms is not None:
            self.message_send_duration_ms.add_value(duration_ms)
    
    def track_message_received(self, duration_ms: Optional[float] = None) -> None:
        """Track a message being received.
        
        Args:
            duration_ms: The time taken to receive the message in milliseconds
        """
        self.message_received_total.increment()
        if duration_ms is not None:
            self.message_receive_duration_ms.add_value(duration_ms)
    
    def track_error(self, error_category: ErrorCategory, error_message: str) -> None:
        """Track an error.
        
        Args:
            error_category: The category of the error
            error_message: The error message
        """
        self.errors_total.increment()
        if error_category in self.errors_by_category:
            self.errors_by_category[error_category].increment()
        self.last_error_timestamp = time.time()
        self.last_error_message = error_message
    
    def track_queue_metrics(self, queue_depth: int, max_depth: int) -> None:
        """Track queue metrics.
        
        Args:
            queue_depth: Current queue depth
            max_depth: Maximum queue depth
        """
        self.queue_depth.set(queue_depth)
        if max_depth > 0:
            self.queue_utilization_percent.set((queue_depth / max_depth) * 100)
        else:
            self.queue_utilization_percent.set(0)
    
    def update_time_based_metrics(self) -> None:
        """Update time-based metrics like uptime."""
        current_time = time.time()
        self.uptime_seconds.set(current_time - self.start_time)
        
        if self.last_connection_time is not None:
            self.connection_uptime_seconds.set(current_time - self.last_connection_time)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics as a dictionary.
        
        Returns:
            Dict containing all metrics with their current values
        """
        self.update_time_based_metrics()
        
        metrics = {
            "operational": {
                "message_sent_total": self.message_sent_total.value,
                "message_received_total": self.message_received_total.value,
                "errors_total": self.errors_total.value,
                "connection_attempts_total": self.connection_attempts_total.value,
                "reconnection_attempts_total": self.reconnection_attempts_total.value,
            },
            "performance": {
                "message_send_duration_ms": {
                    "count": self.message_send_duration_ms.count,
                    "sum": self.message_send_duration_ms.sum,
                    "percentiles": self.message_send_duration_ms.percentiles
                },
                "message_receive_duration_ms": {
                    "count": self.message_receive_duration_ms.count,
                    "sum": self.message_receive_duration_ms.sum,
                    "percentiles": self.message_receive_duration_ms.percentiles
                },
            },
            "state": {
                "connection_state": self.connection_state.value,
                "queue_depth": self.queue_depth.value,
                "queue_utilization_percent": self.queue_utilization_percent.value,
            },
            "errors": {
                "by_category": {
                    category.value: metric.value 
                    for category, metric in self.errors_by_category.items()
                },
                "last_error_timestamp": self.last_error_timestamp,
                "last_error_message": self.last_error_message,
            },
            "system": {
                "uptime_seconds": self.uptime_seconds.value,
                "connection_uptime_seconds": self.connection_uptime_seconds.value,
            },
            "metadata": {
                "client_id": self.client_id,
                "binding_type": self.binding_type,
                "connection_info": self.connection_info
            }
        }
        
        return metrics
    
    def reset_histogram_metrics(self) -> None:
        """Reset histogram metrics while keeping counters."""
        self.message_send_duration_ms.reset()
        self.message_receive_duration_ms.reset() 