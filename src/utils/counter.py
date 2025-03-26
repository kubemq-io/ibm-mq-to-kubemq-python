"""
Atomic counter implementation for thread-safe metric tracking.
"""
import threading
from typing import Union, Optional


class AtomicCounter:
    """Thread-safe counter implementation.
    
    This class provides atomic operations for incrementing, adding, and
    reading counter values in a multi-threaded environment.
    """
    
    def __init__(self, initial_value: int = 0):
        """Initialize the atomic counter.
        
        Args:
            initial_value: The initial value of the counter
            
        Raises:
            ValueError: If the initial value is negative
        """
        if initial_value < 0:
            raise ValueError("Initial counter value cannot be negative")
        
        self._value = initial_value
        self._lock = threading.Lock()
    
    def increment(self, return_value: bool = False) -> Optional[int]:
        """Increment the counter by 1.
        
        Args:
            return_value: Whether to return the new value
            
        Returns:
            The new value of the counter if return_value is True, otherwise None
        """
        with self._lock:
            self._value += 1
            return self._value if return_value else None
    
    def add(self, amount: Union[int, float], return_value: bool = False) -> Optional[Union[int, float]]:
        """Add a value to the counter.
        
        Args:
            amount: The amount to add to the counter
            return_value: Whether to return the new value
            
        Returns:
            The new value of the counter if return_value is True, otherwise None
            
        Raises:
            ValueError: If amount is negative and would result in a negative counter
        """
        if not isinstance(amount, (int, float)):
            raise TypeError("Amount must be a number (int or float)")
        
        with self._lock:
            new_value = self._value + amount
            if new_value < 0:
                raise ValueError("Counter cannot be negative, attempted to add: " + str(amount))
            
            self._value = new_value
            return self._value if return_value else None
    
    def reset(self, value: Union[int, float] = 0) -> None:
        """Reset the counter to a specific value.
        
        Args:
            value: The value to reset the counter to, defaults to 0
            
        Raises:
            ValueError: If the new value is negative
        """
        if not isinstance(value, (int, float)):
            raise TypeError("Value must be a number (int or float)")
        
        if value < 0:
            raise ValueError("Counter cannot be reset to a negative value")
        
        with self._lock:
            self._value = value
    
    @property
    def value(self) -> Union[int, float]:
        """Get the current value of the counter.
        
        Returns:
            The current value of the counter
        """
        with self._lock:
            return self._value 