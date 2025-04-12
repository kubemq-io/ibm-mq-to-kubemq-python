from __future__ import annotations
import asyncio
from typing import List, Dict, Any

from src.bindings.binding import Binding
from src.bindings.config import BindingsConfig, BindingType, BindingConfig
from src.bindings.exceptions import BindingConfigError
from src.common.log import get_logger
from src.metrics.service import MetricsService
from src.metrics.binding import BindingMetricsHelper


class Bindings:
    def __init__(self, config_path: str, metrics_service: MetricsService):
        self.logger = get_logger("binding_manager")
        self.config = BindingsConfig.load(config_path)
        self.metrics_service = metrics_service
        self.bindings: List[Binding] = []

    def init(self):
        try:
            for binding_config in self.config.bindings:
                self.logger.info(f"Initializing binding: {binding_config.name}")

                if binding_config.type == BindingType.IBM_MQ_TO_KUBEMQ:
                    source_type = "ibm_mq"
                    target_type = "kubemq"
                    source_queue = binding_config.source.queue_name
                    target_queue = binding_config.target.queue_name
                elif binding_config.type == BindingType.KUBEMQ_TO_IBM_MQ:
                    source_type = "kubemq"
                    target_type = "ibm_mq"
                    source_queue = binding_config.source.queue_name
                    target_queue = binding_config.target.queue_name
                elif binding_config.type == BindingType.KUBEMQ_TO_KUBEMQ:
                    source_type = "kubemq"
                    target_type = "kubemq"
                    source_queue = binding_config.source.queue_name
                    target_queue = binding_config.target.queue_name
                else:
                    raise BindingConfigError(
                        f"Unsupported binding type: {binding_config.type}"
                    )

                if not source_queue:
                    raise BindingConfigError(
                        f"Missing 'queue_name' in source properties for binding '{binding_config.name}'"
                    )
                if not target_queue:
                    raise BindingConfigError(
                        f"Missing 'queue_name' in target properties for binding '{binding_config.name}'"
                    )

                source_metrics = BindingMetricsHelper(
                    metrics_service=self.metrics_service,
                    binding_name=binding_config.name,
                    binding_type=source_type,
                    queue_name=source_queue,
                )
                target_metrics = BindingMetricsHelper(
                    metrics_service=self.metrics_service,
                    binding_name=binding_config.name,
                    binding_type=target_type,
                    queue_name=target_queue,
                )

                new_binding = Binding(binding_config, source_metrics, target_metrics)
                new_binding.init()
                self.bindings.append(new_binding)
        except Exception as e:
            self.logger.exception(f"Error initializing bindings: {str(e)}")
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
