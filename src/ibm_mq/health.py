"""
Health check module for IBM MQ connections.

This module provides functionality to check the health of an IBM MQ connection,
focusing on core connection availability without metrics collection.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import asyncio

from pymqi import Queue, QueueManager

import pymqi


@dataclass
class HealthCheckResult:
    """Result of a health check operation.
    
    Attributes:
        status (str): Overall health status
        details (Dict): Additional health check details
        errors (Dict): Any errors encountered during health check
    """
    status: str
    details: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health check result to a dictionary.
        
        Returns:
            Dict containing health check data
        """
        return {
            "status": self.status,
            "details": self.details,
            "errors": self.errors
        }


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


def get_connection_health_status(is_connected: bool, last_error: Optional[Exception] = None) -> str:
    """Get connection health status based on current connection state.
    
    Args:
        is_connected: Current connection status
        last_error: Last error encountered (if any)
        
    Returns:
        str: Health status string (healthy, degraded, or unhealthy)
    """
    if is_connected:
        return HealthStatus.HEALTHY
    elif last_error is not None:
        return HealthStatus.UNHEALTHY
    else:
        return HealthStatus.DEGRADED


def check_queue_health(queue: Queue) -> Dict[str, Any]:
    """Check health of queue.
    
    Args:
        queue: The MQ queue to check
        
    Returns:
        Dict: Results of health check
    """
    result = {
        "status": HealthStatus.HEALTHY,
        "errors": {}
    }
    
    try:
        # Check if queue is open
        _ = queue.inquire(pymqi.CMQC.MQIA_CURRENT_Q_DEPTH)
    except Exception as e:
        result["status"] = HealthStatus.UNHEALTHY
        result["errors"]["queue_check"] = str(e)
    
    return result


async def perform_health_check(
    is_connected: bool, 
    queue_manager: Optional[QueueManager], 
    queue: Optional[Queue],
    last_error: Optional[Exception] = None
) -> HealthCheckResult:
    """Perform a health check on the IBM MQ connection.
    
    Args:
        is_connected: Current connection status
        queue_manager: The MQ queue manager connection
        queue: The MQ queue
        last_error: Last error encountered
        
    Returns:
        HealthCheckResult: Result of health check
    """
    overall_status = get_connection_health_status(is_connected, last_error)
    details = {
        "connection_status": "connected" if is_connected else "disconnected",
    }
    errors = {}
    
    # If we have a connection error, add it to errors
    if last_error is not None:
        errors["last_error"] = str(last_error)
    
    # If connected, check queue manager and queue health
    if is_connected and queue_manager is not None and queue is not None:
        try:
            # Check if queue manager is accessible
            _ = queue_manager.inquire(pymqi.CMQC.MQCA_Q_MGR_NAME)
            details["queue_manager_accessible"] = True
        except Exception as e:
            details["queue_manager_accessible"] = False
            errors["queue_manager_check"] = str(e)
            overall_status = HealthStatus.DEGRADED
        
        # Check queue health
        queue_health = check_queue_health(queue)
        details["queue_accessible"] = queue_health["status"] == HealthStatus.HEALTHY
        if queue_health["status"] != HealthStatus.HEALTHY:
            errors.update(queue_health["errors"])
            # Degrade overall status if queue has issues
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
    
    return HealthCheckResult(
        status=overall_status,
        details=details,
        errors=errors
    ) 