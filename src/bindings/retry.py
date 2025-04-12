import asyncio


class RetryWrapper:
    """
    A wrapper class to retry an async function call if it raises an exception.
    """

    def __init__(self, max_retries: int = 3, delay_seconds: float = 1.0, logger=None):
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds
        self.logger = logger

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, self.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt >= self.max_retries:
                        if self.logger:
                            self.logger.error(
                                f"Maximum retry attempts ({self.max_retries}) reached. "
                                f"Last error: {str(e)}"
                            )
                        raise e
                    
                    if self.logger:
                        self.logger.warning(
                            f"Attempt {attempt}/{self.max_retries} failed: {str(e)}. "
                            f"Retrying in {self.delay_seconds} seconds..."
                        )
                        
                    # Wait before next retry
                    await asyncio.sleep(self.delay_seconds)
            
            # This should never be reached but just in case
            assert last_exception is not None
            raise last_exception

        return wrapper
