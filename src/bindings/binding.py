from __future__ import annotations
from typing import Dict, Any

from src.bindings.config import BindingConfig, BindingType
from src.bindings.connection import Connection
from src.bindings.exceptions import BindingConfigError
from src.common.log import get_logger
from src.kubemq.client import KubeMQClient
from src.kubemq.config import Config as KubeMQConfig
from src.metrics.binding import BindingMetricsHelper
from src.bindings.retry import RetryWrapper


class Binding:
    def __init__(self, config: BindingConfig, source_metrics: BindingMetricsHelper, target_metrics: BindingMetricsHelper):
        self.config = config
        self.source_metrics = source_metrics
        self.target_metrics = target_metrics
        self.source: Connection | None = None
        self.target: Connection | None = None
        self.logger = get_logger(f"binding.{self.config.name}")

    def init(self):
        """
        Dynamically selects the source/target classes and configs
        based on binding type, initializes them, and passes metrics helpers.
        """

        if self.config.type == BindingType.IBM_MQ_TO_KUBEMQ:
            from src.ibm_mq.client import IBMMQClient
            from src.ibm_mq.config import Config as IBMMQConfig

            source_client_cls, source_config_cls, source_err = (
                IBMMQClient,
                IBMMQConfig,
                "ibmmq source",
            )
            target_client_cls, target_config_cls, target_err = (
                KubeMQClient,
                KubeMQConfig,
                "kubemq target",
            )
            source_metrics_helper = self.source_metrics
            target_metrics_helper = self.target_metrics
        elif self.config.type == BindingType.KUBEMQ_TO_IBM_MQ:
            from src.ibm_mq.client import IBMMQClient
            from src.ibm_mq.config import Config as IBMMQConfig
            source_client_cls, source_config_cls, source_err = (
                KubeMQClient,
                KubeMQConfig,
                "kubemq source",
            )
            target_client_cls, target_config_cls, target_err = (
                IBMMQClient,
                IBMMQConfig,
                "ibmmq target",
            )
            source_metrics_helper = self.source_metrics
            target_metrics_helper = self.target_metrics
        elif self.config.type == BindingType.KUBEMQ_TO_KUBEMQ:
            source_client_cls, source_config_cls, source_err = (
                KubeMQClient,
                KubeMQConfig,
                "kubemq source",
            )
            target_client_cls, target_config_cls, target_err = (
                KubeMQClient,
                KubeMQConfig,
                "kubemq target",
            )
            source_metrics_helper = self.source_metrics
            target_metrics_helper = self.target_metrics
        else:
            raise BindingConfigError(f"Unsupported binding type: {self.config.type}")

        # Initialize source
        try:
            source_cfg = source_config_cls(**self.config.source.model_dump())
            source_cfg.binding_name = self.config.name
            source_cfg.binding_type = "source"
            self.source = source_client_cls(source_cfg, source_metrics_helper)
        except Exception as e:
            msg = f"Error initializing {source_err}: {str(e)}"
            self.logger.exception(msg)
            raise BindingConfigError(msg)

        # Initialize target
        try:
            target_cfg = target_config_cls(**self.config.target.model_dump())
            target_cfg.binding_name = self.config.name
            target_cfg.binding_type = "target"
            self.target = target_client_cls(target_cfg, target_metrics_helper)
        except Exception as e:
            msg = f"Error initializing {target_err}: {str(e)}"
            self.logger.exception(msg)
            raise BindingConfigError(msg)

    async def start(self):
        await self.target.start()
        await self.source.start()
        
        # Create a wrapped version of target's send_message with retry logic
        if not self.config.retry.disable_retry:
            retry_wrapper = RetryWrapper(
                max_retries=self.config.retry.max_retries,
                delay_seconds=self.config.retry.delay_seconds,
                logger=self.logger
            )
            
            @retry_wrapper
            async def wrapped_send_message(message: bytes):
                try:
                    return await self.target.send_message(message)
                except Exception as e:
                    self.logger.error(f"Error in target send_message: {str(e)}")
                    # Re-raise to trigger retry logic
                    raise
            
            await self.source.poll(wrapped_send_message)
        else:
            # Use original callback if retry is disabled
            await self.source.poll(self.target.send_message)

    async def stop(self):
        await self.source.stop()
        await self.target.stop()

    async def is_healthy(self) -> bool:
        """Check if the binding is healthy.

        Returns:
            bool: True if both source and target are healthy, False otherwise
        """
        try:
            source_healthy = await self.source.is_healthy() if self.source else False
            target_healthy = await self.target.is_healthy() if self.target else False

            return source_healthy and target_healthy
        except Exception as e:
            self.logger.error(f"Error checking binding health: {str(e)}")
            return False

    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health status including source and target.

        Returns:
            Dict containing health information for the binding and its components
        """
        try:
            # Check source health
            source_healthy = await self.source.is_healthy() if self.source else False

            # Check target health
            target_healthy = await self.target.is_healthy() if self.target else False

            # Determine binding health
            binding_healthy = source_healthy and target_healthy

            # Create health response
            health = {
                "binding_name": self.config.name,
                "binding_type": self.config.type.value,
                "is_healthy": binding_healthy,
                "source": {"is_healthy": source_healthy},
                "target": {"is_healthy": target_healthy},
            }

            return health
        except Exception as e:
            self.logger.error(f"Error getting detailed health: {str(e)}")
            return {
                "binding_name": self.config.name,
                "binding_type": self.config.type.value,
                "is_healthy": False,
                "error": str(e),
                "source": {"is_healthy": False},
                "target": {"is_healthy": False},
            }
