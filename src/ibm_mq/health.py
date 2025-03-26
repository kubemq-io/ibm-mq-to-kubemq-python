"""
Health check module for IBM MQ connections.

This module provides functionality to check the health of an IBM MQ connection,
focusing solely on basic connection status without intermediary states.
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
        status (str): Overall health status (healthy or unhealthy)
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
    UNHEALTHY = "unhealthy"


def get_connection_health_status(is_connected: bool, last_error: Optional[Exception] = None) -> str:
    """Get connection health status based on current connection state.
    
    Args:
        is_connected: Current connection status
        last_error: Last error encountered (if any)
        
    Returns:
        str: Health status string (healthy or unhealthy)
    """
    if is_connected and last_error is None:
        return HealthStatus.HEALTHY
    else:
        return HealthStatus.UNHEALTHY


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
        queue: The MQ queue (not used)
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
        overall_status = HealthStatus.UNHEALTHY
    
    # Check that we have a connection - any issue means unhealthy
    if is_connected and queue_manager is not None:
        try:
            # Basic connection check
            _ = queue_manager.inquire(pymqi.CMQC.MQCA_Q_MGR_NAME)
        except Exception as e:
            errors["queue_manager_check"] = str(e)
            # Set status to unhealthy and update connection status to disconnected
            overall_status = HealthStatus.UNHEALTHY
            details["connection_status"] = "disconnected"
    
    return HealthCheckResult(
        status=overall_status,
        details=details,
        errors=errors
    ) 