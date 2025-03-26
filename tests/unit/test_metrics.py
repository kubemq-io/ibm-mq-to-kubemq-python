import unittest
import time
from src.bindings.metrics import (
    MetricsCollector, 
    BindingMetricsCollector, 
    SystemMetricsCollector,
    ConnectionState,
    ErrorCategory
)


class TestMetricsCollector(unittest.TestCase):
    """Test the MetricsCollector class."""
    
    def setUp(self):
        """Set up the test case."""
        self.collector = MetricsCollector(
            client_id="test-client",
            binding_type="test-binding",
            connection_info={"host": "localhost", "port": "1234"}
        )
    
    def test_track_message_sent(self):
        """Test tracking message sent metrics."""
        # Track a message
        message_size = 256
        self.collector.track_message_sent(message_size)
        
        # Verify metrics
        metrics = self.collector.get_metrics()
        self.assertEqual(metrics["messages_sent_total"], 1)
        self.assertEqual(metrics["messages_sent_volume"], message_size)
        self.assertIsNotNone(metrics["last_message_sent_time"])
    
    def test_track_message_received(self):
        """Test tracking message received metrics."""
        # Track a message
        message_size = 512
        self.collector.track_message_received(message_size)
        
        # Verify metrics
        metrics = self.collector.get_metrics()
        self.assertEqual(metrics["messages_received_total"], 1)
        self.assertEqual(metrics["messages_received_volume"], message_size)
        self.assertIsNotNone(metrics["last_message_received_time"])
    
    def test_track_error(self):
        """Test tracking error metrics."""
        # Track errors
        self.collector.track_error(ErrorCategory.SEND, "Test send error", is_send=True)
        self.collector.track_error(ErrorCategory.RECEIVE, "Test receive error", is_send=False)
        
        # Verify metrics
        metrics = self.collector.get_metrics()
        self.assertEqual(metrics["errors_sent_total"], 1)
        self.assertEqual(metrics["errors_received_total"], 1)
        self.assertIsNotNone(metrics["last_error_sent_time"])
        self.assertIsNotNone(metrics["last_error_received_time"])
    
    def test_track_reconnection(self):
        """Test tracking reconnection metrics."""
        # Track reconnection attempts and failures
        self.collector.track_reconnection_attempt()
        self.collector.track_reconnection_failure()
        
        # Verify metrics
        metrics = self.collector.get_metrics()
        self.assertEqual(metrics["reconnection_attempts_total"], 1)
        self.assertEqual(metrics["reconnection_failures_total"], 1)
        self.assertIsNotNone(metrics["last_reconnection_time"])
        self.assertIsNotNone(metrics["last_reconnection_error_time"])
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        # Test current timestamp
        now = time.time()
        formatted = self.collector.format_timestamp(now)
        self.assertIn("just now", formatted)
        
        # Test timestamp from 30 minutes ago
        thirty_min_ago = now - 30 * 60
        formatted = self.collector.format_timestamp(thirty_min_ago)
        self.assertIn("since 30m ago", formatted)
        
        # Test timestamp from 2 hours ago
        two_hours_ago = now - 2 * 60 * 60
        formatted = self.collector.format_timestamp(two_hours_ago)
        self.assertIn("since 2h ago", formatted)
        
        # Test timestamp from 3 days ago
        three_days_ago = now - 3 * 24 * 60 * 60
        formatted = self.collector.format_timestamp(three_days_ago)
        self.assertIn("since 3d ago", formatted)


class TestBindingMetricsCollector(unittest.TestCase):
    """Test the BindingMetricsCollector class."""
    
    def setUp(self):
        """Set up the test case."""
        self.source_collector = MetricsCollector(
            client_id="source-client",
            binding_type="source",
            connection_info={"host": "localhost", "port": "1234"}
        )
        
        self.target_collector = MetricsCollector(
            client_id="target-client",
            binding_type="target",
            connection_info={"host": "remotehost", "port": "5678"}
        )
        
        self.binding_collector = BindingMetricsCollector(
            binding_name="test-binding",
            source_collector=self.source_collector,
            target_collector=self.target_collector
        )
    
    def test_aggregation(self):
        """Test metric aggregation from source and target."""
        # Add metrics to source
        self.source_collector.track_message_received(100)
        self.source_collector.track_error(ErrorCategory.RECEIVE, "Source error", is_send=False)
        self.source_collector.track_reconnection_attempt()
        
        # Add metrics to target
        self.target_collector.track_message_sent(200)
        self.target_collector.track_error(ErrorCategory.SEND, "Target error", is_send=True)
        self.target_collector.track_reconnection_failure()
        
        # Get aggregated metrics
        metrics = self.binding_collector.get_metrics()
        
        # Verify aggregated metrics
        self.assertEqual(metrics["name"], "test-binding")
        self.assertEqual(metrics["messages_received_total"], 1)
        self.assertEqual(metrics["messages_received_volume"], 100)
        self.assertEqual(metrics["messages_sent_total"], 1)
        self.assertEqual(metrics["messages_sent_volume"], 200)
        self.assertEqual(metrics["errors_sent_total"], 1)
        self.assertEqual(metrics["errors_received_total"], 1)
        self.assertEqual(metrics["reconnection_attempts_total"], 1)
        self.assertEqual(metrics["reconnection_failures_total"], 1)
        
        # Verify timestamps are copied
        self.assertEqual(
            metrics["last_message_received_time"],
            self.source_collector.format_timestamp(self.source_collector.last_message_received_time)
        )
        self.assertEqual(
            metrics["last_message_sent_time"],
            self.target_collector.format_timestamp(self.target_collector.last_message_sent_time)
        )


class TestSystemMetricsCollector(unittest.TestCase):
    """Test the SystemMetricsCollector class."""
    
    def setUp(self):
        """Set up the test case."""
        # Create collectors for first binding
        self.source1 = MetricsCollector(
            client_id="source1",
            binding_type="source",
            connection_info={"host": "localhost", "port": "1234"}
        )
        
        self.target1 = MetricsCollector(
            client_id="target1",
            binding_type="target",
            connection_info={"host": "remotehost1", "port": "5678"}
        )
        
        self.binding1 = BindingMetricsCollector(
            binding_name="binding1",
            source_collector=self.source1,
            target_collector=self.target1
        )
        
        # Create collectors for second binding
        self.source2 = MetricsCollector(
            client_id="source2",
            binding_type="source",
            connection_info={"host": "localhost", "port": "1234"}
        )
        
        self.target2 = MetricsCollector(
            client_id="target2",
            binding_type="target",
            connection_info={"host": "remotehost2", "port": "5678"}
        )
        
        self.binding2 = BindingMetricsCollector(
            binding_name="binding2",
            source_collector=self.source2,
            target_collector=self.target2
        )
        
        # Create system collector
        self.system = SystemMetricsCollector()
        self.system.add_binding("binding1", self.binding1)
        self.system.add_binding("binding2", self.binding2)
    
    def test_system_aggregation(self):
        """Test system-level metric aggregation."""
        # Add metrics to first binding
        self.source1.track_message_received(100)
        self.target1.track_message_sent(200)
        self.source1.track_error(ErrorCategory.RECEIVE, "Source1 error", is_send=False)
        
        # Add metrics to second binding
        self.source2.track_message_received(150)
        self.target2.track_message_sent(250)
        self.target2.track_error(ErrorCategory.SEND, "Target2 error", is_send=True)
        
        # Get system metrics
        metrics = self.system.get_metrics()
        
        # Verify system aggregation
        system_metrics = metrics["system"]
        self.assertEqual(system_metrics["messages_received_total"], 2)
        self.assertEqual(system_metrics["messages_received_volume"], 250)  # 100 + 150
        self.assertEqual(system_metrics["messages_sent_total"], 2)
        self.assertEqual(system_metrics["messages_sent_volume"], 450)  # 200 + 250
        self.assertEqual(system_metrics["errors_received_total"], 1)
        self.assertEqual(system_metrics["errors_sent_total"], 1)
        self.assertEqual(system_metrics["bindings_total"], 2)
        
        # Verify bindings are included
        self.assertIn("binding1", metrics["bindings"])
        self.assertIn("binding2", metrics["bindings"])
    
    def test_remove_binding(self):
        """Test removing a binding from the system."""
        # Add metrics to both bindings
        self.source1.track_message_received(100)
        self.source2.track_message_received(150)
        
        # Remove one binding
        self.system.remove_binding("binding1")
        
        # Get system metrics
        metrics = self.system.get_metrics()
        
        # Verify updated system metrics
        self.assertEqual(metrics["system"]["bindings_total"], 1)
        self.assertEqual(metrics["system"]["messages_received_total"], 1)
        self.assertEqual(metrics["system"]["messages_received_volume"], 150)
        
        # Verify only the remaining binding is included
        self.assertNotIn("binding1", metrics["bindings"])
        self.assertIn("binding2", metrics["bindings"])


if __name__ == "__main__":
    unittest.main() 