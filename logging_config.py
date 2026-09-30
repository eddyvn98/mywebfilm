import logging
import os
from logging.handlers import RotatingFileHandler


def configure_logging(data_dir):
    os.makedirs(data_dir, exist_ok=True)
    logger = logging.getLogger()
    if getattr(logger, '_cinema_configured', False):
        return

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        os.path.join(data_dir, 'cinema.log'),
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger._cinema_configured = True
