import logging

# Set up logger
logger = logging.getLogger('testforge')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def log_event(message):
    """Log an event."""
    logger.info(message)

def log_error(message):
    """Log an error."""
    logger.error(message)

def log_warning(message):
    """Log a warning."""
    logger.warning(message)

