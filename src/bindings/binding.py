from src.bindings.config import BindingConfig, BindingType
from src.bindings.connection import Connection
from src.bindings.exceptions import BindingConfigError
from src.common.log import get_logger
from src.ibm_mq.client import IBMMQClient
from src.kubemq.client import KubeMQClient
from src.kubemq.config import Config as KubeMQConfig
from src.ibm_mq.config import Config as IBMMQConfig


class Binding:
    def __init__(self, config: BindingConfig):
        self.config = config
        self.source: Connection | None = None
        self.target: Connection | None = None
        self.logger = get_logger(f"binding.{self.config.name}")

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

    async def start(self):
        await self.target.start()
        await self.source.start()
        await self.source.poll(self.target.send_message)

    async def stop(self):
        await self.source.stop()
        await self.target.stop()
