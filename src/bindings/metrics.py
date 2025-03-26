"""Metrics collection for messaging bindings.

This module provides a simplified metrics collection system for messaging operations,
tracking operational counters and timestamps for sources and targets.
"""

import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Any, List, Union


class ConnectionState(Enum):
    """Possible connection states for tracking metrics."""
    UNKNOWN = "unknown"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"


class ErrorCategory(Enum):
    """Categories of errors for metrics tracking."""
    UNKNOWN = "unknown"
    RECEIVE = "receive"
    SEND = "send"
    CONNECTION = "connection"
    INTERNAL = "internal"


class MetricsCollector:
    """Base metrics collector for a component.
    
    This class collects metrics for a single component (source or target).
    """
    
    def __init__(self, client_id: str, binding_type: str, connection_info: Dict[str, str]):
        """Initialize the metrics collector.
        
        Args:
            client_id: Client ID or component name
            binding_type: Type of the component (e.g. 'kubemq', 'ibm_mq')
            connection_info: Connection information
        """
        from src.utils.counter import AtomicCounter
        
        self.client_id = client_id
        self.binding_type = binding_type
        self.connection_info = connection_info
        
        # Operational metrics
        self.messages_received_total = AtomicCounter()
        self.messages_received_volume = AtomicCounter()
        self.messages_sent_total = AtomicCounter()
        self.messages_sent_volume = AtomicCounter()
        self.errors_sent_total = AtomicCounter()
        self.errors_received_total = AtomicCounter()
        self.reconnection_attempts_total = AtomicCounter()
        self.reconnection_failures_total = AtomicCounter()
        
        # Connection state
        self.connection_state = ConnectionState.DISCONNECTED
        
        # Timestamps
        self.last_message_received_time = None
        self.last_message_sent_time = None
        self.last_error_received_time = None 
        self.last_error_sent_time = None
        self.last_reconnection_time = None
        self.last_reconnection_error_time = None
        self.last_connection_time = None
    
    def track_message_received(self, message_size: int) -> None:
        """Track a received message.
        
        Args:
            message_size: Size of the message in bytes
        """
        self.messages_received_total.increment()
        self.messages_received_volume.add(message_size)
        self.last_message_received_time = time.time()
    
    def track_message_sent(self, message_size: int) -> None:
        """Track a sent message.
        
        Args:
            message_size: Size of the message in bytes
        """
        self.messages_sent_total.increment()
        self.messages_sent_volume.add(message_size)
        self.last_message_sent_time = time.time()
    
    def track_error(self, category: ErrorCategory, message: str, is_send: bool = False) -> None:
        """Track an error.
        
        Args:
            category: Error category
            message: Error message
            is_send: Whether this is a send error (vs. receive)
        """
        if is_send:
            self.errors_sent_total.increment()
            self.last_error_sent_time = time.time()
        else:
            self.errors_received_total.increment()
            self.last_error_received_time = time.time()
    
    def track_reconnection_attempt(self) -> None:
        """Track a reconnection attempt."""
        self.reconnection_attempts_total.increment()
        self.last_reconnection_time = time.time()
    
    def track_reconnection_failure(self) -> None:
        """Track a reconnection failure."""
        self.reconnection_failures_total.increment()
        self.last_reconnection_error_time = time.time()
    
    def track_connection(self) -> None:
        """Track a successful connection."""
        self.last_connection_time = time.time()
    
    def track_connection_state(self, state: ConnectionState) -> None:
        """Track connection state changes.
        
        Args:
            state: The new connection state
        """
        self.connection_state = state
        if state == ConnectionState.CONNECTED:
            self.track_connection()
        # Other states don't require special handling
    
    def track_connection_attempt(self) -> None:
        """Track a connection attempt.
        
        Note: This is primarily for compatibility with existing code.
        New code should use track_connection_state with ConnectionState.CONNECTING.
        """
        # Keep for backward compatibility
        pass
    
    def format_timestamp(self, timestamp: Optional[float]) -> Optional[str]:
        """Format a timestamp with UTC time and relative duration.
        
        Args:
            timestamp: Unix timestamp to format
            
        Returns:
            Formatted string with UTC time and relative duration, or None if timestamp is None
            
        Raises:
            ValueError: If the timestamp format is invalid
        """
        if timestamp is None:
            return None
        
        try:
            current_time = time.time()
            dt = datetime.utcfromtimestamp(timestamp)
            now = datetime.utcfromtimestamp(current_time)
            diff = now - dt
            
            # Format the relative time
            if diff < timedelta(minutes=1):
                relative = "just now"
            elif diff < timedelta(hours=1):
                minutes = int(diff.total_seconds() / 60)
                relative = f"since {minutes}m ago"
            elif diff < timedelta(days=1):
                hours = int(diff.total_seconds() / 3600)
                relative = f"since {hours}h ago"
            else:
                days = diff.days
                relative = f"since {days}d ago"
                
            return f"{dt.strftime('%Y-%m-%dT%H:%M:%SZ')} ({relative})"
        except (ValueError, TypeError, OverflowError) as e:
            # Log the error and return a safe default
            return f"Invalid timestamp: {timestamp}"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get component metrics.
        
        Returns:
            Dict containing operational metrics and timestamp information
        """
        current_time = time.time()
        
        metrics = {
            "name": self.client_id,
            "type": self.binding_type,
            "messages_received_total": self.messages_received_total.value,
            "messages_received_volume": self.messages_received_volume.value,
            "messages_sent_total": self.messages_sent_total.value,
            "messages_sent_volume": self.messages_sent_volume.value,
            "errors_sent_total": self.errors_sent_total.value,
            "errors_received_total": self.errors_received_total.value,
            "reconnection_attempts_total": self.reconnection_attempts_total.value,
            "reconnection_failures_total": self.reconnection_failures_total.value,
            # Store both formatted and raw timestamps
            "last_message_received_time": self.format_timestamp(self.last_message_received_time),
            "last_message_received_timestamp": self.last_message_received_time,
            "last_message_sent_time": self.format_timestamp(self.last_message_sent_time),
            "last_message_sent_timestamp": self.last_message_sent_time,
            "last_error_received_time": self.format_timestamp(self.last_error_received_time),
            "last_error_received_timestamp": self.last_error_received_time,
            "last_error_sent_time": self.format_timestamp(self.last_error_sent_time),
            "last_error_sent_timestamp": self.last_error_sent_time,
            "last_reconnection_time": self.format_timestamp(self.last_reconnection_time),
            "last_reconnection_timestamp": self.last_reconnection_time,
            "last_reconnection_error_time": self.format_timestamp(self.last_reconnection_error_time),
            "last_reconnection_error_timestamp": self.last_reconnection_error_time,
        }
        
        return metrics


class BindingMetricsCollector:
    """Collector for binding metrics.
    
    This class aggregates metrics from source and target components.
    """
    
    def __init__(self, binding_name: str, source_collector: MetricsCollector, target_collector: MetricsCollector):
        """Initialize the binding metrics collector.
        
        Args:
            binding_name: Name of the binding
            source_collector: Source component metrics collector
            target_collector: Target component metrics collector
        """
        self.binding_name = binding_name
        self.source_collector = source_collector
        self.target_collector = target_collector
    
    @staticmethod
    def get_latest_timestamp(timestamp1: Optional[float], timestamp2: Optional[float]) -> Optional[float]:
        """Get the latest of two timestamps.
        
        Args:
            timestamp1: First timestamp
            timestamp2: Second timestamp
            
        Returns:
            The latest timestamp, or None if both are None
        """
        if timestamp1 is None and timestamp2 is None:
            return None
            
        if timestamp1 is None:
            return timestamp2
            
        if timestamp2 is None:
            return timestamp1
            
        return max(timestamp1, timestamp2)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics for the binding.
        
        Returns:
            Dict containing aggregated metrics from source and target
        """
        source_metrics = self.source_collector.get_metrics()
        target_metrics = self.target_collector.get_metrics()
        
        # Aggregate counter metrics
        messages_received_total = source_metrics["messages_received_total"]
        messages_received_volume = source_metrics["messages_received_volume"]
        messages_sent_total = target_metrics["messages_sent_total"]
        messages_sent_volume = target_metrics["messages_sent_volume"]
        errors_sent_total = target_metrics["errors_sent_total"]
        errors_received_total = source_metrics["errors_received_total"]
        reconnection_attempts_total = (
            source_metrics["reconnection_attempts_total"] +
            target_metrics["reconnection_attempts_total"]
        )
        reconnection_failures_total = (
            source_metrics["reconnection_failures_total"] +
            target_metrics["reconnection_failures_total"]
        )
        
        # Get the latest timestamps
        last_message_received_time = self.source_collector.last_message_received_time
        last_message_sent_time = self.target_collector.last_message_sent_time
        last_error_received_time = self.source_collector.last_error_received_time
        last_error_sent_time = self.target_collector.last_error_sent_time
        last_reconnection_time = self.get_latest_timestamp(
            self.source_collector.last_reconnection_time,
            self.target_collector.last_reconnection_time
        )
        last_reconnection_error_time = self.get_latest_timestamp(
            self.source_collector.last_reconnection_error_time,
            self.target_collector.last_reconnection_error_time
        )
        
        # Create binding metrics
        metrics = {
            "name": self.binding_name,
            "messages_received_total": messages_received_total,
            "messages_received_volume": messages_received_volume,
            "messages_sent_total": messages_sent_total,
            "messages_sent_volume": messages_sent_volume,
            "errors_sent_total": errors_sent_total,
            "errors_received_total": errors_received_total,
            "reconnection_attempts_total": reconnection_attempts_total,
            "reconnection_failures_total": reconnection_failures_total,
            "last_message_received_time": source_metrics["last_message_received_time"],
            "last_message_received_timestamp": last_message_received_time,
            "last_message_sent_time": target_metrics["last_message_sent_time"],
            "last_message_sent_timestamp": last_message_sent_time,
            "last_error_received_time": source_metrics["last_error_received_time"],
            "last_error_received_timestamp": last_error_received_time,
            "last_error_sent_time": target_metrics["last_error_sent_time"],
            "last_error_sent_timestamp": last_error_sent_time,
            "last_reconnection_time": self.source_collector.format_timestamp(last_reconnection_time),
            "last_reconnection_timestamp": last_reconnection_time,
            "last_reconnection_error_time": self.source_collector.format_timestamp(last_reconnection_error_time),
            "last_reconnection_error_timestamp": last_reconnection_error_time,
            "components": {
                "source": source_metrics,
                "target": target_metrics
            }
        }
        
        return metrics


class SystemMetricsCollector:
    """Collector for system-wide metrics.
    
    This class aggregates metrics from all bindings.
    """
    
    def __init__(self):
        """Initialize the system metrics collector."""
        self.binding_collectors: Dict[str, BindingMetricsCollector] = {}
    
    def add_binding(self, binding_name: str, binding_collector: BindingMetricsCollector) -> None:
        """Add a binding metrics collector.
        
        Args:
            binding_name: Name of the binding
            binding_collector: Binding metrics collector
        """
        self.binding_collectors[binding_name] = binding_collector
    
    def remove_binding(self, binding_name: str) -> None:
        """Remove a binding metrics collector.
        
        Args:
            binding_name: Name of the binding to remove
        """
        if binding_name in self.binding_collectors:
            del self.binding_collectors[binding_name]
    
    @staticmethod
    def get_latest_timestamp(timestamps: List[Optional[float]]) -> Optional[float]:
        """Get the latest timestamp from a list.
        
        Args:
            timestamps: List of timestamps
            
        Returns:
            The latest timestamp, or None if the list is empty or contains only None values
        """
        # Filter out None values
        valid_timestamps = [ts for ts in timestamps if ts is not None]
        if not valid_timestamps:
            return None
        return max(valid_timestamps)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics for the entire system.
        
        Returns:
            Dict containing system-wide metrics and all binding metrics
        """
        # Initialize system counters
        messages_received_total = 0
        messages_received_volume = 0
        messages_sent_total = 0
        messages_sent_volume = 0
        errors_sent_total = 0
        errors_received_total = 0
        reconnection_attempts_total = 0
        reconnection_failures_total = 0
        
        # Initialize timestamp collection lists
        last_message_received_times: List[Optional[float]] = []
        last_message_sent_times: List[Optional[float]] = []
        last_error_received_times: List[Optional[float]] = []
        last_error_sent_times: List[Optional[float]] = []
        last_reconnection_times: List[Optional[float]] = []
        last_reconnection_error_times: List[Optional[float]] = []
        
        # Collect binding metrics
        binding_metrics = {}
        for name, collector in self.binding_collectors.items():
            binding_data = collector.get_metrics()
            binding_metrics[name] = binding_data
            
            # Aggregate counters
            messages_received_total += binding_data["messages_received_total"]
            messages_received_volume += binding_data["messages_received_volume"]
            messages_sent_total += binding_data["messages_sent_total"]
            messages_sent_volume += binding_data["messages_sent_volume"]
            errors_sent_total += binding_data["errors_sent_total"]
            errors_received_total += binding_data["errors_received_total"]
            reconnection_attempts_total += binding_data["reconnection_attempts_total"]
            reconnection_failures_total += binding_data["reconnection_failures_total"]
            
            # Collect timestamps
            source = collector.source_collector
            target = collector.target_collector
            
            if source.last_message_received_time is not None:
                last_message_received_times.append(source.last_message_received_time)
            if target.last_message_sent_time is not None:
                last_message_sent_times.append(target.last_message_sent_time)
            if source.last_error_received_time is not None:
                last_error_received_times.append(source.last_error_received_time)
            if target.last_error_sent_time is not None:
                last_error_sent_times.append(target.last_error_sent_time)
            if source.last_reconnection_time is not None:
                last_reconnection_times.append(source.last_reconnection_time)
            if target.last_reconnection_time is not None:
                last_reconnection_times.append(target.last_reconnection_time)
            if source.last_reconnection_error_time is not None:
                last_reconnection_error_times.append(source.last_reconnection_error_time)
            if target.last_reconnection_error_time is not None:
                last_reconnection_error_times.append(target.last_reconnection_error_time)
        
        # Get the latest timestamps
        last_message_received_time = self.get_latest_timestamp(last_message_received_times)
        last_message_sent_time = self.get_latest_timestamp(last_message_sent_times)
        last_error_received_time = self.get_latest_timestamp(last_error_received_times)
        last_error_sent_time = self.get_latest_timestamp(last_error_sent_times)
        last_reconnection_time = self.get_latest_timestamp(last_reconnection_times)
        last_reconnection_error_time = self.get_latest_timestamp(last_reconnection_error_times)
        
        # Create a reference formatter for timestamps
        formatter = MetricsCollector("system", "system", {})
        
        # Create system metrics
        metrics = {
            "system": {
                "messages_received_total": messages_received_total,
                "messages_received_volume": messages_received_volume,
                "messages_sent_total": messages_sent_total,
                "messages_sent_volume": messages_sent_volume,
                "errors_sent_total": errors_sent_total,
                "errors_received_total": errors_received_total,
                "reconnection_attempts_total": reconnection_attempts_total,
                "reconnection_failures_total": reconnection_failures_total,
                "bindings_total": len(self.binding_collectors),
                "last_message_received_time": formatter.format_timestamp(last_message_received_time),
                "last_message_received_timestamp": last_message_received_time,
                "last_message_sent_time": formatter.format_timestamp(last_message_sent_time),
                "last_message_sent_timestamp": last_message_sent_time,
                "last_error_received_time": formatter.format_timestamp(last_error_received_time),
                "last_error_received_timestamp": last_error_received_time,
                "last_error_sent_time": formatter.format_timestamp(last_error_sent_time),
                "last_error_sent_timestamp": last_error_sent_time,
                "last_reconnection_time": formatter.format_timestamp(last_reconnection_time),
                "last_reconnection_timestamp": last_reconnection_time,
                "last_reconnection_error_time": formatter.format_timestamp(last_reconnection_error_time),
                "last_reconnection_error_timestamp": last_reconnection_error_time,
            },
            "bindings": binding_metrics
        }
        
        return metrics 