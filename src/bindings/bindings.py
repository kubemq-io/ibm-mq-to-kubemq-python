import asyncio
from typing import List

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
