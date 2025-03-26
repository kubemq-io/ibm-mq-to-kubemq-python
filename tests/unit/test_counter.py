"""Unit tests for the AtomicCounter class."""
import unittest
from src.utils.counter import AtomicCounter


class TestAtomicCounter(unittest.TestCase):
    """Test the AtomicCounter class."""
    
    def test_init(self):
        """Test initialization with default and custom values."""
        # Default initialization
        counter = AtomicCounter()
        self.assertEqual(counter.value, 0)
        
        # Custom initialization
        counter = AtomicCounter(10)
        self.assertEqual(counter.value, 10)
        
        # Invalid initialization
        with self.assertRaises(ValueError):
            AtomicCounter(-1)
    
    def test_increment(self):
        """Test the increment method."""
        counter = AtomicCounter()
        
        # Test increment without return value
        result = counter.increment()
        self.assertIsNone(result)
        self.assertEqual(counter.value, 1)
        
        # Test increment with return value
        result = counter.increment(return_value=True)
        self.assertEqual(result, 2)
        self.assertEqual(counter.value, 2)
    
    def test_add(self):
        """Test the add method."""
        counter = AtomicCounter(10)
        
        # Test add without return value
        result = counter.add(5)
        self.assertIsNone(result)
        self.assertEqual(counter.value, 15)
        
        # Test add with return value
        result = counter.add(5, return_value=True)
        self.assertEqual(result, 20)
        self.assertEqual(counter.value, 20)
        
        # Test add with float
        result = counter.add(0.5, return_value=True)
        self.assertEqual(result, 20.5)
        self.assertEqual(counter.value, 20.5)
        
        # Test add with invalid type
        with self.assertRaises(TypeError):
            counter.add("5")
        
        # Test add with negative value that would make counter negative
        with self.assertRaises(ValueError):
            counter.add(-30)
        
        # Test add with negative value that keeps counter positive
        result = counter.add(-0.5, return_value=True)
        self.assertEqual(result, 20.0)
        self.assertEqual(counter.value, 20.0)
    
    def test_reset(self):
        """Test the reset method."""
        counter = AtomicCounter(10)
        
        # Test reset to default (0)
        counter.reset()
        self.assertEqual(counter.value, 0)
        
        # Test reset to custom value
        counter.reset(15)
        self.assertEqual(counter.value, 15)
        
        # Test reset with invalid type
        with self.assertRaises(TypeError):
            counter.reset("5")
        
        # Test reset with negative value
        with self.assertRaises(ValueError):
            counter.reset(-5)
    
    def test_value_property(self):
        """Test the value property."""
        counter = AtomicCounter(10)
        self.assertEqual(counter.value, 10)
        
        counter.increment()
        self.assertEqual(counter.value, 11)
        
        counter.add(5)
        self.assertEqual(counter.value, 16)
        
        counter.reset(20)
        self.assertEqual(counter.value, 20)


if __name__ == "__main__":
    unittest.main() 