from typing import Dict, Any

from src.bindings.config import BindingConfig, BindingType
from src.bindings.connection import Connection
from src.bindings.exceptions import BindingConfigError
from src.common.log import get_logger
from src.ibm_mq.client import IBMMQClient
from src.kubemq.client import KubeMQClient
from src.kubemq.config import Config as KubeMQConfig
from src.ibm_mq.config import Config as IBMMQConfig
from src.bindings.metrics import BindingMetricsCollector


class Binding:
    def __init__(self, config: BindingConfig):
        self.config = config
        self.source: Connection | None = None
        self.target: Connection | None = None
        self.logger = get_logger(f"binding.{self.config.name}")
        self.metrics_collector: BindingMetricsCollector | None = None

    def init(self):
        """
        Dynamically selects the source/target classes and configs
        based on binding type, and initializes them.
        """

        if self.config.type == BindingType.IBM_MQ_TO_KUBEMQ:
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
        elif self.config.type == BindingType.KUBEMQ_TO_IBM_MQ:
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
        else:
            raise BindingConfigError(f"Unsupported binding type: {self.config.type}")

        # Initialize source
        try:
            source_cfg = source_config_cls(**self.config.source.model_dump())
            source_cfg.binding_name = self.config.name
            source_cfg.binding_type = "source"
            self.source = source_client_cls(source_cfg)
        except Exception as e:
            msg = f"Error {source_err} initialization: {str(e)}"
            self.logger.exception(msg)
            raise BindingConfigError(msg)

        # Initialize target
        try:
            target_cfg = target_config_cls(**self.config.target.model_dump())
            target_cfg.binding_name = self.config.name
            target_cfg.binding_type = "target"
            self.target = target_client_cls(target_cfg)
        except Exception as e:
            msg = f"Error {target_err} initialization: {str(e)}"
            self.logger.error(msg)
            raise BindingConfigError(msg)
            
        # Initialize binding metrics collector
        if self.source and self.target:
            self.metrics_collector = BindingMetricsCollector(
                self.config.name,
                self.source.metrics,
                self.target.metrics
            )

    async def start(self):
        await self.target.start()
        await self.source.start()
        await self.source.poll(self.target.send_message)

    async def stop(self):
        await self.source.stop()
        await self.target.stop()
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from both source and target connections and aggregate them.
        
        Returns:
            Dict containing aggregated metrics from source and target connections
        """
        if self.metrics_collector:
            return self.metrics_collector.get_metrics()
        
        # Fallback if metrics collector is not initialized
        metrics = {
            "binding_name": self.config.name,
            "binding_type": self.config.type.value,
            "source": None,
            "target": None
        }
        
        if self.source:
            metrics["source"] = self.source.get_metrics()
            
        if self.target:
            metrics["target"] = self.target.get_metrics()
            
        return metrics
        
    async def check_health(self) -> Dict[str, Any]:
        """Check health of both source and target connections.
        
        Returns:
            Dict containing health information for the binding
        """
        health = {
            "binding_name": self.config.name,
            "binding_type": self.config.type.value,
            "status": "healthy",
            "source": None,
            "target": None
        }
        
        try:
            if self.source:
                source_health = await self.source.check_health()
                health["source"] = source_health
                if source_health["status"] != "healthy":
                    health["status"] = "unhealthy"
        except Exception as e:
            self.logger.error(f"Error checking source health: {str(e)}")
            health["status"] = "unhealthy"
            health["source"] = {"status": "unhealthy", "error": str(e)}
            
        try:
            if self.target:
                target_health = await self.target.check_health()
                health["target"] = target_health
                if target_health["status"] != "healthy":
                    health["status"] = "unhealthy"
        except Exception as e:
            self.logger.error(f"Error checking target health: {str(e)}")
            health["status"] = "unhealthy"
            health["target"] = {"status": "unhealthy", "error": str(e)}
            
        return health
