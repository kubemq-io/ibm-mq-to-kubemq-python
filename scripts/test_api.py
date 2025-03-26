"""Test script for the API server."""
import asyncio
import anyio
import requests
import time

from src.bindings.bindings import Bindings
from src.api.app import APIServer
from src.common.log import get_logger

logger = get_logger("test_api")


async def test_api():
    """Test the API server with a simple binding configuration."""
    # Create a bindings instance with a test configuration
    config_path = "config.yaml"  # Use your test config
    bindings = Bindings(config_path)
    bindings.init()
    
    # Create and start the API server
    api_server = APIServer(bindings, port=9000)
    await api_server.start()
    
    logger.info("API server started on port 9000")
    logger.info("Starting bindings")
    await bindings.start()
    
    # Let the server start up
    await asyncio.sleep(2)
    
    try:
        # Test the API endpoints
        logger.info("Testing API endpoints...")
        
        # Root endpoint
        logger.info("Testing root endpoint...")
        response = requests.get("http://localhost:9000/")
        logger.info(f"Root endpoint response: {response.status_code}")
        logger.info(f"Root endpoint data: {response.json()}")
        
        # Health endpoint
        logger.info("Testing health endpoint...")
        response = requests.get("http://localhost:9000/health")
        logger.info(f"Health endpoint response: {response.status_code}")
        logger.info(f"Health endpoint data: {response.json()}")
        
        # Metrics endpoint
        logger.info("Testing metrics endpoint...")
        response = requests.get("http://localhost:9000/metrics")
        logger.info(f"Metrics endpoint response: {response.status_code}")
        logger.info(f"Metrics endpoint data: {response.json()}")
        
        logger.info("API tests completed successfully")
        
    except Exception as e:
        logger.error(f"Error testing API: {str(e)}")
    finally:
        # Cleanup
        logger.info("Stopping API server and bindings...")
        await api_server.stop()
        await bindings.stop()
        logger.info("API server and bindings stopped")


if __name__ == "__main__":
    anyio.run(test_api) 