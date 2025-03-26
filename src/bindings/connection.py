from abc import ABC, abstractmethod
from typing import Dict, Any


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

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Check the health of the connection.
        
        Returns:
            Dict containing health status information
        """
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics for this connection.
        
        Returns:
            Dict containing all metrics data
        """
        pass
