import os
import yaml
from enum import Enum
from typing import Dict, Any, Union

from pydantic import BaseModel, Field
from src.kubemq.config import Config as KubeMQConfig
from src.ibm_mq.config import Config as IBMMQConfig


class BindingType(Enum):
    KUBEMQ_TO_IBM_MQ = "kubemq_to_ibm_mq"
    IBM_MQ_TO_KUBEMQ = "ibm_mq_to_kubemq"


class BindingConfig(BaseModel):
    name: str = Field(default=None, description="Name of the binding")
    type: BindingType = Field(default=None, description="Type of binding")
    source: Union[KubeMQConfig, IBMMQConfig] = Field(
        default=None, description="Source configuration"
    )
    target: Union[KubeMQConfig, IBMMQConfig] = Field(
        default=None, description="Target configuration"
    )


class BindingsConfig(BaseModel):
    bindings: list[BindingConfig] = Field(
        default_factory=list, description="List of bindings"
    )

    @classmethod
    def load(cls, config_path: str) -> "BindingsConfig":
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        try:
            with open(config_path, "r") as file:
                yaml_data: Dict[Any, Any] = yaml.safe_load(file)

            # Pre-process the bindings to create proper config objects
            if "bindings" in yaml_data:
                for binding in yaml_data["bindings"]:
                    binding_type = BindingType(binding["type"])

                    # Set correct config types based on binding type
                    if binding_type == BindingType.KUBEMQ_TO_IBM_MQ:
                        binding["source"] = KubeMQConfig(**binding["source"])
                        binding["target"] = IBMMQConfig(**binding["target"])
                    else:  # IBM_MQ_TO_KUBEMQ
                        binding["source"] = IBMMQConfig(**binding["source"])
                        binding["target"] = KubeMQConfig(**binding["target"])

            return BindingsConfig(**yaml_data)
        except Exception as e:
            raise ValueError(f"Error loading config file: {str(e)}")
