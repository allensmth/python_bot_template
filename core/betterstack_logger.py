from logtail import LogtailHandler
import logging

handler = LogtailHandler(source_token="iWkusA4Wy58Y5KiufE5MN7hU")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.handlers = []
logger.addHandler(handler)
