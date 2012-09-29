import logging

LOG_FORMAT = "[%(asctime)s] %(name)s %(levelname)s %(message)s"


def set_up_logging():
    stderr = logging.StreamHandler()
    stderr.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(stderr)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
