import logging
import traceback

# Configure logging
LOG_FILE = "tmp.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
def log(message):
    # Log the message
    logging.info(message)
    # Print the message
    print(message)
    
def log_warning(message):
    # Log a warning-level message
    logging.warning(message)
    # Print the message
    print(message)

def log_error(message):
    logging.error(message)
    # If an exception occurred, log the stack trace
    if isinstance(message, Exception):
        trace = traceback.format_exc()
        logging.error("Stack Trace:\n" + trace)