import asyncio
from typing import List, Dict, Any

from src.bindings.binding import Binding
from src.bindings.config import BindingsConfig
from src.common.log import get_logger


class Bindings:
    def __init__(self, config_path: str):
        self.logger = get_logger("binding_manager")
        self.config = BindingsConfig.load(config_path)
        self.bindings: List[Binding] = []

    def init(self):
        try:
            for binding in self.config.bindings:
                self.logger.info(f"Initializing binding: {binding.name}")
                new_binding = Binding(binding)
                new_binding.init()
                self.bindings.append(new_binding)
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

    async def is_healthy(self) -> bool:
        """Check if all bindings are healthy.

        Returns:
            bool: True if all bindings are healthy, False otherwise
        """
        for binding in self.bindings:
            try:
                if not await binding.is_healthy():
                    return False
            except Exception as e:
                self.logger.error(
                    f"Error checking health for binding {binding.config.name}: {str(e)}"
                )
                return False

        return True

    async def get_detailed_health_status(self) -> Dict[str, Any]:
        """Get detailed health status for all bindings.

        Returns:
            Dict containing detailed health information for all bindings
        """
        # Get overall system health
        system_healthy = await self.is_healthy()

        health = {
            "bindings_count": len(self.bindings),
            "is_healthy": system_healthy,
            "bindings": {},
        }

        # Get health for each binding
        for binding in self.bindings:
            try:
                binding_health = await binding.get_detailed_health()
                health["bindings"][binding.config.name] = binding_health
            except Exception as e:
                self.logger.error(
                    f"Error checking health for binding {binding.config.name}: {str(e)}"
                )
                health["bindings"][binding.config.name] = {
                    "binding_name": binding.config.name,
                    "is_healthy": False,
                    "error": str(e),
                    "source": {"is_healthy": False},
                    "target": {"is_healthy": False},
                }

        return health
