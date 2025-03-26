"""Metrics routes for the API."""
from typing import Dict, Any
from fastapi import APIRouter, Depends

from src.api.utils import format_response, handle_binding_not_found, handle_server_error
from src.bindings.bindings import Bindings


# Create router
router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
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
async def get_all_metrics(bindings: Bindings = Depends(get_bindings)) -> Dict[str, Any]:
    """Get metrics for all bindings.
    
    Returns:
        Dict containing metrics for all bindings
    """
    try:
        metrics = bindings.get_all_metrics()
        return format_response(metrics)
    except Exception as e:
        handle_server_error(e)


@router.get("/{binding_name}")
async def get_binding_metrics(binding_name: str, bindings: Bindings = Depends(get_bindings)) -> Dict[str, Any]:
    """Get metrics for a specific binding.
    
    Args:
        binding_name: Name of the binding to get metrics for
        
    Returns:
        Dict containing metrics for the specified binding
    """
    try:
        metrics = await bindings.get_binding_metrics(binding_name)
        return format_response(metrics)
    except ValueError:
        handle_binding_not_found(binding_name)
    except Exception as e:
        handle_server_error(e) 