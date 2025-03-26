import asyncio
from typing import List, Dict, Any

from src.bindings.binding import Binding
from src.bindings.config import BindingsConfig
from src.common.log import get_logger
from src.bindings.metrics import SystemMetricsCollector


class Bindings:
    def __init__(self, config_path: str):
        self.logger = get_logger("binding_manager")
        self.config = BindingsConfig.load(config_path)
        self.bindings: List[Binding] = []
        self.system_metrics = SystemMetricsCollector()

    def init(self):
        try:
            for binding in self.config.bindings:
                self.logger.info(f"Initializing binding: {binding.name}")
                new_binding = Binding(binding)
                new_binding.init()
                self.bindings.append(new_binding)
                
                # Add binding to system metrics if it has a metrics collector
                if new_binding.metrics_collector:
                    self.system_metrics.add_binding(new_binding.config.name, new_binding.metrics_collector)
        except Exception as e:
            raise Exception(f"Error initializing bindings: {str(e)}")

    async def start(self):
        tasks = []
        for binding in self.bindings:
            tasks.append(binding.start())

        await asyncio.gather(*tasks)

    async def stop(self):
        tasks = []
        for binding in self.bindings:
            tasks.append(binding.stop())

        await asyncio.gather(*tasks)
        
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics from all bindings.
        
        Returns:
            Dict containing system-level metrics and metrics from all bindings
        """
        # Use system metrics collector for aggregated metrics
        return self.system_metrics.get_metrics()
    
    async def check_all_health(self) -> Dict[str, Any]:
        """Check health of all bindings.
        
        Returns:
            Dict containing health information for all bindings
        """
        health = {
            "bindings_count": len(self.bindings),
            "overall_status": "healthy",
            "bindings": {}
        }
        
        for binding in self.bindings:
            try:
                binding_health = await binding.check_health()
                health["bindings"][binding.config.name] = binding_health
                
                # Update overall status based on binding status
                if binding_health["status"] == "unhealthy":
                    health["overall_status"] = "unhealthy"
            except Exception as e:
                self.logger.error(f"Error checking health for binding {binding.config.name}: {str(e)}")
                health["bindings"][binding.config.name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health["overall_status"] = "unhealthy"
                
        return health
        
    async def get_binding_metrics(self, binding_name: str) -> Dict[str, Any]:
        """Get metrics for a specific binding.
        
        Args:
            binding_name: Name of the binding to get metrics for
            
        Returns:
            Dict containing metrics for the specified binding or error if not found
            
        Raises:
            ValueError: If binding with the specified name is not found
        """
        for binding in self.bindings:
            if binding.config.name == binding_name:
                return binding.get_metrics()
                
        raise ValueError(f"Binding with name '{binding_name}' not found")
        
    async def get_binding_health(self, binding_name: str) -> Dict[str, Any]:
        """Check health for a specific binding.
        
        Args:
            binding_name: Name of the binding to check health for
            
        Returns:
            Dict containing health information for the specified binding
            
        Raises:
            ValueError: If binding with the specified name is not found
        """
        for binding in self.bindings:
            if binding.config.name == binding_name:
                return await binding.check_health()
                
        raise ValueError(f"Binding with name '{binding_name}' not found")
