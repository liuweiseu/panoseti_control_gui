import logging
from rich.logging import RichHandler
from pathlib import Path
from datetime import datetime

# create logger
#
def create_logger(logfile, tag, mode='w', level=logging.DEBUG):
    logger = logging.getLogger(tag)
    logger.setLevel(level)
    logformat = logging.Formatter('%(levelname)s - %(asctime)s - %(name)s - %(message)s')
    # write log to log file
    fhandler = logging.FileHandler(logfile, mode=mode)
    fhandler.setFormatter(logformat)
    fhandler.setLevel(logging.DEBUG)
    # write log to terminal (Warning and Error messages only)
    shandler = logging.StreamHandler()
    shandler.setFormatter(logformat)
    shandler.setLevel(logging.WARNING)
    if logger.handlers:
        logger.handlers.clear()
    # add handlers
    logger.addHandler(fhandler)
    logger.addHandler(shandler)

def make_rich_logger(name: str, clevel=logging.INFO, flevel=logging.DEBUG, mode='w') -> logging.Logger:
    """
    Sets up a logger with a RichHandler for console output and a FileHandler
    for writing logs to a file. Also silences noisy third-party loggers.

    Args:
        name (str): The name for the logger (e.g., 'daq_data').
        level (int): The logging level (e.g., logging.INFO).

    Returns:
        logging.Logger: A configured logger instance.
    """
    # The 'watchfiles' logger can be verbose, so we set its level higher.
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    # define log directory and file path
    log_dir = Path("./logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / f"{name}_{datetime.now().strftime('%Y-%m-%d')}.log"

    # Get the logger and set its level.
    # We use getLogger(name) to get our specific application logger.
    logger = logging.getLogger(name)
    logger.setLevel(flevel)

    # Prevent messages from being passed to the root logger
    logger.propagate = False

    # Configure and add the RichHandler for console output
    # This handler is for pretty-printing logs to the terminal.
    console_handler = RichHandler(
        level=clevel,
        show_time=True,
        show_level=True,
        show_path=False, # Set to False for cleaner output
        rich_tracebacks=True,
        tracebacks_theme="monokai",
    )
    console_handler.setFormatter(logging.Formatter("[%(funcName)s()] %(message)s", datefmt="%H:%M:%S"))

    # Configure and add the FileHandler for file output
    # This handler writes logs to the file defined above.
    file_handler = logging.FileHandler(log_file_path, mode=mode)
    file_handler.setLevel(flevel)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Add handlers to the logger, but only if they haven't been added already
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger