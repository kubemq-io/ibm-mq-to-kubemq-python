"""Health check mechanism for IBM MQ connections.

This module provides functionality to check the health status of IBM MQ
connections, including connection state, queue accessibility and performance metrics.
"""

import time
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List

import pymqi


class HealthStatus(Enum):
    """Possible health status values for IBM MQ connections."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheckResult:
    """Result of a health check operation."""
    
    def __init__(self):
        """Initialize a new health check result."""
        self.status: HealthStatus = HealthStatus.UNKNOWN
        self.timestamp: datetime = datetime.now()
        self.response_time_ms: float = 0
        self.details: Dict[str, Any] = {}
        self.metrics: Dict[str, Any] = {}
        self.errors: List[str] = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert health check result to a dictionary.
        
        Returns:
            Dict containing all health check information
        """
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms,
            "details": self.details,
            "metrics": self.metrics,
            "errors": self.errors
        }


async def check_queue_manager_health(queue_manager: pymqi.QueueManager) -> bool:
    """Check if a queue manager is responsive.
    
    Args:
        queue_manager: The queue manager to check
        
    Returns:
        bool: True if the queue manager is responsive
    """
    try:
        # Ping the queue manager (minimal operation to check connectivity)
        queue_manager.inquire(pymqi.CMQC.MQCA_Q_MGR_NAME)
        return True
    except Exception:
        return False


async def check_queue_health(queue: pymqi.Queue) -> Dict[str, Any]:
    """Check the health of a queue.
    
    Args:
        queue: The queue to check
        
    Returns:
        Dict containing queue information and health status
    """
    queue_info = {}
    
    try:
        # Try to retrieve queue depth and other key metrics
        queue_info["queue_depth"] = queue.inquire(pymqi.CMQC.MQIA_CURRENT_Q_DEPTH)
        queue_info["max_depth"] = queue.inquire(pymqi.CMQC.MQIA_MAX_Q_DEPTH)
        queue_info["open_input_count"] = queue.inquire(pymqi.CMQC.MQIA_OPEN_INPUT_COUNT)
        queue_info["open_output_count"] = queue.inquire(pymqi.CMQC.MQIA_OPEN_OUTPUT_COUNT)
        
        # Calculate queue usage percentage
        if queue_info["max_depth"] > 0:
            queue_info["usage_percent"] = (queue_info["queue_depth"] / queue_info["max_depth"]) * 100
        else:
            queue_info["usage_percent"] = 0
            
        # Determine queue health based on depth
        if queue_info["usage_percent"] > 90:
            queue_info["status"] = HealthStatus.DEGRADED.value
        else:
            queue_info["status"] = HealthStatus.HEALTHY.value
            
        return queue_info
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY.value,
            "error": str(e)
        }


def get_connection_health_status(
    is_connected: bool, 
    last_error: Optional[Exception], 
    reconnect_attempts: int, 
    max_reconnect_attempts: int
) -> HealthStatus:
    """Determine the health status of a connection.
    
    Args:
        is_connected: Whether the connection is currently established
        last_error: The last error that occurred, if any
        reconnect_attempts: Number of reconnection attempts made
        max_reconnect_attempts: Maximum number of reconnection attempts allowed
        
    Returns:
        HealthStatus: The health status of the connection
    """
    if not is_connected:
        return HealthStatus.UNHEALTHY
    
    # If connected but has had to reconnect multiple times
    if reconnect_attempts > 0:
        # If nearing max reconnect attempts
        if max_reconnect_attempts > 0 and reconnect_attempts > (max_reconnect_attempts * 0.7):
            return HealthStatus.DEGRADED
        
    # Connected and stable
    return HealthStatus.HEALTHY


async def perform_health_check(
    is_connected: bool,
    queue_manager: Optional[pymqi.QueueManager],
    queue: Optional[pymqi.Queue],
    last_error: Optional[Exception] = None,
    reconnect_attempts: int = 0,
    max_reconnect_attempts: int = 0,
    detailed: bool = False
) -> HealthCheckResult:
    """Perform a comprehensive health check of the IBM MQ connection.
    
    Args:
        is_connected: Whether the connection is currently established
        queue_manager: The queue manager to check
        queue: The queue to check
        last_error: The last error that occurred, if any
        reconnect_attempts: Number of reconnection attempts made
        max_reconnect_attempts: Maximum number of reconnection attempts allowed
        detailed: Whether to perform detailed checks (may be more resource intensive)
        
    Returns:
        HealthCheckResult: The result of the health check
    """
    result = HealthCheckResult()
    start_time = time.time()
    
    # Check basic connection status
    if not is_connected:
        result.status = HealthStatus.UNHEALTHY
        result.errors.append("Not connected to IBM MQ")
        result.details["connection_status"] = "disconnected"
        if last_error:
            result.errors.append(f"Last error: {str(last_error)}")
        result.response_time_ms = (time.time() - start_time) * 1000
        return result
    
    result.details["connection_status"] = "connected"
    result.metrics["reconnect_attempts"] = reconnect_attempts
    
    if max_reconnect_attempts > 0:
        result.metrics["max_reconnect_attempts"] = max_reconnect_attempts
    
    # Check queue manager health
    if queue_manager:
        try:
            qmgr_healthy = await check_queue_manager_health(queue_manager)
            result.details["queue_manager_responsive"] = qmgr_healthy
            
            if not qmgr_healthy:
                result.status = HealthStatus.DEGRADED
                result.errors.append("Queue manager is not responsive")
        except Exception as e:
            result.errors.append(f"Error checking queue manager: {str(e)}")
            result.status = HealthStatus.DEGRADED
    
    # Check queue health
    if queue and detailed:
        try:
            queue_health = await check_queue_health(queue)
            result.details["queue_info"] = queue_health
            
            if queue_health.get("status") == HealthStatus.DEGRADED.value:
                if result.status != HealthStatus.UNHEALTHY:
                    result.status = HealthStatus.DEGRADED
                    
            if queue_health.get("status") == HealthStatus.UNHEALTHY.value:
                result.status = HealthStatus.UNHEALTHY
                result.errors.append(queue_health.get("error", "Queue is unhealthy"))
        except Exception as e:
            result.errors.append(f"Error checking queue: {str(e)}")
            if result.status != HealthStatus.UNHEALTHY:
                result.status = HealthStatus.DEGRADED
    
    # Set overall status if not already set to a non-UNKNOWN value
    if result.status == HealthStatus.UNKNOWN:
        result.status = get_connection_health_status(
            is_connected, last_error, reconnect_attempts, max_reconnect_attempts
        )
    
    # Calculate response time
    result.response_time_ms = (time.time() - start_time) * 1000
    
    return result 