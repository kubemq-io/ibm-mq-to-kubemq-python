"""Strategy classes for IBM MQ message receiving and sending.

This module contains the strategy pattern implementation for different
IBM MQ message handling modes. It provides abstract base classes and
concrete implementations for various receiver and sender modes.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

import pymqi


class ReceiverStrategy(ABC):
    """Abstract base class for message receiving strategies."""
    
    @abstractmethod
    async def receive_message(self, queue: pymqi.Queue, md: pymqi.MD, gmo: pymqi.GMO) -> Union[bytes, str]:
        """Receive a message from the queue using the specific strategy.
        
        Args:
            queue: The IBM MQ queue to receive from
            md: Message descriptor for the received message
            gmo: Get message options
            
        Returns:
            The received message content
            
        Raises:
            pymqi.MQMIError: For MQ-specific errors
        """
        pass


class DefaultReceiverStrategy(ReceiverStrategy):
    """Default message receiving strategy using standard get method."""
    
    async def receive_message(self, queue: pymqi.Queue, md: pymqi.MD, gmo: pymqi.GMO) -> Union[bytes, str]:
        """Receive a message using the default get method.
        
        Args:
            queue: The IBM MQ queue to receive from
            md: Message descriptor for the received message
            gmo: Get message options
            
        Returns:
            The received message content
        """
        return await asyncio.to_thread(queue.get, None, md, gmo)


class Rfh2ReceiverStrategy(ReceiverStrategy):
    """Message receiving strategy using RFH2 headers."""
    
    async def receive_message(self, queue: pymqi.Queue, md: pymqi.MD, gmo: pymqi.GMO) -> Union[bytes, str]:
        """Receive a message with RFH2 headers.
        
        Args:
            queue: The IBM MQ queue to receive from
            md: Message descriptor for the received message
            gmo: Get message options
            
        Returns:
            The received message content with RFH2 headers
        """
        return await asyncio.to_thread(queue.get_rfh2, None, md, gmo)


class NoRfh2ReceiverStrategy(ReceiverStrategy):
    """Message receiving strategy that strips RFH2 headers."""
    
    async def receive_message(self, queue: pymqi.Queue, md: pymqi.MD, gmo: pymqi.GMO) -> Union[bytes, str]:
        """Receive a message with RFH2 headers stripped.
        
        Args:
            queue: The IBM MQ queue to receive from
            md: Message descriptor for the received message
            gmo: Get message options
            
        Returns:
            The received message content without RFH2 headers
        """
        return await asyncio.to_thread(queue.get_no_rfh2, None, md, gmo)


class SenderStrategy(ABC):
    """Abstract base class for message sending strategies."""
    
    @abstractmethod
    async def send_message(self, queue: pymqi.Queue, message: str, config: Any) -> None:
        """Send a message to the queue using the specific strategy.
        
        Args:
            queue: The IBM MQ queue to send to
            message: The message content to send
            config: Configuration parameters for sending
            
        Raises:
            pymqi.MQMIError: For MQ-specific errors
        """
        pass


class DefaultSenderStrategy(SenderStrategy):
    """Default message sending strategy using standard put method."""
    
    async def send_message(self, queue: pymqi.Queue, message: str, config: Any) -> None:
        """Send a message using the default put method.
        
        Args:
            queue: The IBM MQ queue to send to
            message: The message content to send
            config: Configuration parameters (unused in this strategy)
        """
        await asyncio.to_thread(queue.put, message)


class Rfh2SenderStrategy(SenderStrategy):
    """Message sending strategy using RFH2 headers."""
    
    async def send_message(self, queue: pymqi.Queue, message: str, config: Any) -> None:
        """Send a message with RFH2 headers.
        
        Args:
            queue: The IBM MQ queue to send to
            message: The message content to send
            config: Configuration parameters (unused in this strategy)
        """
        await asyncio.to_thread(queue.put_rfh2, message)


class CustomSenderStrategy(SenderStrategy):
    """Message sending strategy with custom format and CCSID."""
    
    async def send_message(self, queue: pymqi.Queue, message: str, config: Any) -> None:
        """Send a message with custom format and CCSID settings.
        
        Args:
            queue: The IBM MQ queue to send to
            message: The message content to send
            config: Configuration containing format and CCSID settings
        """
        md = pymqi.MD()
        md.Format = config.get_md_format()
        if config.message_ccsid > 0:
            md.CodedCharSetId = config.message_ccsid
        await asyncio.to_thread(queue.put, message, md)


def get_receiver_strategy(mode: Optional[str]) -> ReceiverStrategy:
    """Factory function to get the appropriate receiver strategy.
    
    Args:
        mode: The receiver mode name ('rfh2', 'no_rfh2', 'default', etc.)
        
    Returns:
        The appropriate receiver strategy instance
        
    Raises:
        ValueError: If the mode is not recognized
    """
    # Normalize mode
    if mode is None or mode == "" or mode == "default":
        return DefaultReceiverStrategy()
    elif mode == "rfh2":
        return Rfh2ReceiverStrategy()
    elif mode == "no_rfh2":
        return NoRfh2ReceiverStrategy()
    else:
        raise ValueError(f"Invalid receiver mode: {mode}")


def get_sender_strategy(mode: Optional[str]) -> SenderStrategy:
    """Factory function to get the appropriate sender strategy.
    
    Args:
        mode: The sender mode name ('rfh2', 'custom', 'default', etc.)
        
    Returns:
        The appropriate sender strategy instance
        
    Raises:
        ValueError: If the mode is not recognized
    """
    # Normalize mode
    if mode is None or mode == "" or mode == "default":
        return DefaultSenderStrategy()
    elif mode == "rfh2":
        return Rfh2SenderStrategy()
    elif mode == "custom":
        return CustomSenderStrategy()
    else:
        raise ValueError(f"Invalid sender mode: {mode}") 