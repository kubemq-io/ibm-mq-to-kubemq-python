"""Test script for verifying the dashboard functionality."""
import asyncio
import anyio
import webbrowser
import os
import time

from src.bindings.bindings import Bindings
from src.common.log import get_logger
from src.api.app import APIServer

logger = get_logger("dashboard_test")


async def test_dashboard():
    """Test the dashboard functionality by starting the API server and opening a browser."""
    try:
        # Load bindings from config file
        config_path = os.environ.get("CONFIG_PATH", "config.yaml")
        logger.info(f"Loading bindings from {config_path}")
        bindings = Bindings(config_path)
        bindings.init()
        
        # Start the API server on port 9000
        port = 9000
        api_server = APIServer(bindings, port=port)
        await api_server.start()
        logger.info(f"API server started on port {port}")
        
        # Open the browser to the dashboard
        dashboard_url = f"http://localhost:{port}/dashboard"
        logger.info(f"Opening dashboard in browser: {dashboard_url}")
        webbrowser.open(dashboard_url)
        
        # Keep the server running for 30 seconds for testing
        logger.info("Dashboard is available for 30 seconds. Press Ctrl+C to exit early.")
        for i in range(30):
            await asyncio.sleep(1)
            remaining = 30 - i - 1
            if remaining % 5 == 0 and remaining > 0:
                logger.info(f"Server will shut down in {remaining} seconds...")
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Error during dashboard test: {str(e)}")
    finally:
        # Stop the API server
        logger.info("Stopping API server")
        if api_server:
            await api_server.stop()
        
        # Stop bindings
        logger.info("Stopping bindings")
        if bindings:
            await bindings.stop()
            
        logger.info("Dashboard test completed")


if __name__ == "__main__":
    anyio.run(test_dashboard) 