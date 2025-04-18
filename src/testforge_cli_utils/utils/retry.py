import time

def retry_test(func, retries=3, delay=5):
    """Retry a function if it fails."""
    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            else:
                raise e

