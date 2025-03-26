"""Health check routes for the API."""
from typing import Dict, Any
from fastapi import APIRouter, Depends

from src.api.utils import format_response, handle_binding_not_found, handle_server_error
from src.bindings.bindings import Bindings


# Create router
router = APIRouter(
    prefix="/health",
    tags=["health"],
)


def get_bindings() -> Bindings:
    """Dependency to get the bindings instance.
    This will be overridden with a proper function in the app.py file.
    
    Returns:
        Bindings: The bindings instance
        
    Note:
        This implementation should never be called directly as it will be
        overridden by the APIServer class. This is just a placeholder.
    """
    # Return None by default - will be overridden
    raise RuntimeError("get_bindings dependency was not properly overridden")


@router.get("/")
async def get_all_health(bindings: Bindings = Depends(get_bindings)) -> Dict[str, Any]:
    """Get health status for all bindings.
    
    Returns:
        Dict containing health status for all bindings
    """
    try:
        health = await bindings.check_all_health()
        return format_response(health)
    except Exception as e:
        handle_server_error(e)


@router.get("/{binding_name}")
async def get_binding_health(binding_name: str, bindings: Bindings = Depends(get_bindings)) -> Dict[str, Any]:
    """Get health status for a specific binding.
    
    Args:
        binding_name: Name of the binding to get health status for
        
    Returns:
        Dict containing health status for the specified binding
    """
    try:
        health = await bindings.get_binding_health(binding_name)
        return format_response(health)
    except ValueError:
        handle_binding_not_found(binding_name)
    except Exception as e:
        handle_server_error(e) 