"""Error classification for IBM MQ operations.

This module provides utilities for classifying IBM MQ errors as transient
(temporary and can be retried) or permanent (requiring intervention).
It helps with making intelligent decisions about retry behaviors.
"""

from enum import Enum
from typing import Dict, Set

import pymqi


class ErrorType(Enum):
    """Classification of error types for recovery strategy decisions."""

    # Error is temporary and operation can be retried
    TRANSIENT = "transient"

    # Error requires reconnection before retry
    CONNECTION = "connection"

    # Error is permanent and requires intervention
    PERMANENT = "permanent"

    # Error is related to configuration
    CONFIGURATION = "configuration"

    # Error when system is shutting down
    SHUTDOWN = "shutdown"


# MQ reason codes that indicate transient errors that can be retried
TRANSIENT_ERRORS: Set[int] = {
    pymqi.CMQC.MQRC_NO_MSG_AVAILABLE,  # No message available when getting with wait
    pymqi.CMQC.MQRC_Q_FULL,  # Queue is full when putting
    pymqi.CMQC.MQRC_RESOURCE_PROBLEM,  # Temporary resource constraint
    pymqi.CMQC.MQRC_PAGESET_ERROR,  # Temporary pageset error
    pymqi.CMQC.MQRC_STORAGE_NOT_AVAILABLE,  # Temporary storage issue
    pymqi.CMQC.MQRC_BACKED_OUT,  # Message backed out
}

# MQ reason codes that indicate connection-related errors
CONNECTION_ERRORS: Set[int] = {
    pymqi.CMQC.MQRC_CONNECTION_BROKEN,  # Connection to queue manager lost
    pymqi.CMQC.MQRC_CONNECTION_ERROR,  # General connection error
    pymqi.CMQC.MQRC_Q_MGR_NOT_AVAILABLE,  # Queue manager not available
    pymqi.CMQC.MQRC_Q_MGR_QUIESCING,  # Queue manager quiescing
    pymqi.CMQC.MQRC_Q_MGR_STOPPING,  # Queue manager stopping
    pymqi.CMQC.MQRC_HOST_NOT_AVAILABLE,  # Host not available
    pymqi.CMQC.MQRC_CHANNEL_NOT_AVAILABLE,  # Channel not available
}

# MQ reason codes that indicate configuration errors
CONFIGURATION_ERRORS: Set[int] = {
    pymqi.CMQC.MQRC_UNKNOWN_OBJECT_NAME,  # Unknown queue or channel name
    pymqi.CMQC.MQRC_NOT_AUTHORIZED,  # Not authorized for operation
    pymqi.CMQC.MQRC_Q_TYPE_ERROR,  # Wrong queue type
    pymqi.CMQC.MQRC_UNKNOWN_REMOTE_Q_MGR,  # Unknown remote queue manager
    pymqi.CMQC.MQRC_UNKNOWN_CHANNEL_NAME,  # Unknown channel name
    pymqi.CMQC.MQRC_SSL_CONFIG_ERROR,  # SSL configuration error
}

# MQ reason codes that indicate system is shutting down
SHUTDOWN_ERRORS: Set[int] = {
    pymqi.CMQC.MQRC_Q_MGR_QUIESCING,  # Queue manager quiescing
    pymqi.CMQC.MQRC_Q_MGR_STOPPING,  # Queue manager stopping
    pymqi.CMQC.MQRC_CONNECTION_QUIESCING,  # Connection quiescing
}


def classify_error(error_reason: int) -> ErrorType:
    """Classify an IBM MQ error based on its reason code.

    Args:
        error_reason: The MQ reason code from the exception

    Returns:
        ErrorType: The classification of the error (TRANSIENT, CONNECTION, etc.)
    """
    if error_reason in TRANSIENT_ERRORS:
        return ErrorType.TRANSIENT
    elif error_reason in CONNECTION_ERRORS:
        return ErrorType.CONNECTION
    elif error_reason in CONFIGURATION_ERRORS:
        return ErrorType.CONFIGURATION
    elif error_reason in SHUTDOWN_ERRORS:
        return ErrorType.SHUTDOWN
    else:
        # Any unclassified error is considered permanent
        return ErrorType.PERMANENT


def is_transient_error(error_reason: int) -> bool:
    """Check if an error is transient and can be retried.

    Args:
        error_reason: The MQ reason code from the exception

    Returns:
        bool: True if the error is transient and can be retried
    """
    return error_reason in TRANSIENT_ERRORS


def is_connection_error(error_reason: int) -> bool:
    """Check if an error is related to connection issues.

    Args:
        error_reason: The MQ reason code from the exception

    Returns:
        bool: True if the error is connection-related
    """
    return error_reason in CONNECTION_ERRORS


def is_configuration_error(error_reason: int) -> bool:
    """Check if an error is related to configuration issues.

    Args:
        error_reason: The MQ reason code from the exception

    Returns:
        bool: True if the error is configuration-related
    """
    return error_reason in CONFIGURATION_ERRORS


def get_retry_recommendation(error_reason: int) -> Dict[str, any]:
    """Get a recommendation for retry strategy based on error classification.

    Args:
        error_reason: The MQ reason code from the exception

    Returns:
        Dict with retry recommendations:
            - should_retry: Whether retry is recommended
            - should_reconnect: Whether reconnection is needed before retry
            - retry_delay: Suggested initial delay before retry (seconds)
            - max_retries: Suggested maximum number of retries (-1 for unlimited)
    """
    error_type = classify_error(error_reason)

    if error_type == ErrorType.TRANSIENT:
        return {
            "should_retry": True,
            "should_reconnect": False,
            "retry_delay": 0.5,
            "max_retries": 5,
            "error_type": error_type,
        }
    elif error_type == ErrorType.CONNECTION:
        return {
            "should_retry": True,
            "should_reconnect": True,
            "retry_delay": 1.0,
            "max_retries": -1,  # Unlimited reconnection attempts
            "error_type": error_type,
        }
    elif error_type == ErrorType.CONFIGURATION:
        return {
            "should_retry": False,
            "should_reconnect": False,
            "retry_delay": 0,
            "max_retries": 0,
            "error_type": error_type,
        }
    elif error_type == ErrorType.SHUTDOWN:
        return {
            "should_retry": True,
            "should_reconnect": True,
            "retry_delay": 5.0,  # Longer delay for shutdown
            "max_retries": 3,
            "error_type": error_type,
        }
    else:  # PERMANENT
        return {
            "should_retry": False,
            "should_reconnect": False,
            "retry_delay": 0,
            "max_retries": 0,
            "error_type": error_type,
        }


def get_error_message(error_reason: int) -> str:
    """Get a human-readable message for an IBM MQ error.

    Args:
        error_reason: The MQ reason code from the exception

    Returns:
        str: A descriptive message about the error
    """
    # Map of error codes to human-readable messages
    error_messages = {
        # Transient errors
        pymqi.CMQC.MQRC_NO_MSG_AVAILABLE: "No message available on the queue",
        pymqi.CMQC.MQRC_Q_FULL: "Queue is full, cannot put message",
        pymqi.CMQC.MQRC_RESOURCE_PROBLEM: "Temporary resource constraint",
        pymqi.CMQC.MQRC_BACKED_OUT: "Message was backed out",
        # Connection errors
        pymqi.CMQC.MQRC_CONNECTION_BROKEN: "Connection to IBM MQ server was lost",
        pymqi.CMQC.MQRC_CONNECTION_ERROR: "Error establishing connection to IBM MQ",
        pymqi.CMQC.MQRC_Q_MGR_NOT_AVAILABLE: "Queue manager is not available",
        pymqi.CMQC.MQRC_HOST_NOT_AVAILABLE: "IBM MQ host is not available",
        # Configuration errors
        pymqi.CMQC.MQRC_UNKNOWN_OBJECT_NAME: "Queue name not found or incorrect",
        pymqi.CMQC.MQRC_NOT_AUTHORIZED: "Not authorized to access the requested resource",
        pymqi.CMQC.MQRC_SSL_CONFIG_ERROR: "SSL configuration error",
        # Shutdown errors
        pymqi.CMQC.MQRC_Q_MGR_QUIESCING: "Queue manager is quiescing",
        pymqi.CMQC.MQRC_Q_MGR_STOPPING: "Queue manager is stopping",
    }

    return error_messages.get(
        error_reason, f"IBM MQ error with reason code: {error_reason}"
    )
