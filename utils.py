import logging
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