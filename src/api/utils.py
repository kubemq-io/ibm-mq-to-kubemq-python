"""Utility functions for the API."""
from typing import Dict, Any, Optional
from fastapi import HTTPException, status


def format_response(data: Any, success: bool = True, message: Optional[str] = None) -> Dict[str, Any]:
    """Format a standard API response.
    
    Args:
        data: The data to include in the response
        success: Whether the request was successful
        message: Optional message to include in the response
        
    Returns:
        Dict containing formatted response
    """
    response = {
        "success": success,
        "data": data
    }
    
    if message:
        response["message"] = message
        
    return response


def handle_binding_not_found(binding_name: str) -> None:
    """Handle binding not found error.
    
    Args:
        binding_name: Name of the binding that was not found
        
    Raises:
        HTTPException: 404 error with binding not found message
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Binding '{binding_name}' not found"
    )


def handle_server_error(error: Exception) -> None:
    """Handle server error.
    
    Args:
        error: The exception that occurred
        
    Raises:
        HTTPException: 500 error with error message
    """
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Server error: {str(error)}"
    ) 