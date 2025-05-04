import functools
import logging
import time

# Setup logging
logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries=5, initial_delay=1, backoff_factor=2, exceptions=(Exception,)
):
    """
    Decorator for retrying a function with exponential backoff

    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        logger.info(
                            f"Retry attempt {attempt}/{max_retries} for {func.__name__}"
                        )

                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Final retry attempt {attempt} failed for {func.__name__}"
                        )
                        raise last_exception

                    logger.warning(
                        f"{func.__name__} failed on attempt {attempt + 1}/{max_retries}: {str(e)}"
                        f" - retrying in {delay} seconds"
                    )

                    time.sleep(delay)
                    delay *= backoff_factor

            # This should never be reached due to the raise in the loop
            raise last_exception

        return wrapper

    return decorator
