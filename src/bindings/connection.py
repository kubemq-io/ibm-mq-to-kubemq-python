from abc import ABC, abstractmethod


class Connection(ABC):
    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    async def poll(self, callback):
        pass

    @abstractmethod
    async def send_message(self, message: bytes):
        pass
