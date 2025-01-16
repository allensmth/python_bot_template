from logtail import LogtailHandler
import logging
import os

LOG_FORMAT = "%(asctime)s %(message)s"
DEFAULT_LEVEL = logging.DEBUG

class LogWrapper:
    PATH = './logs'

    def __init__(self, name, mode="w", betterstack_token=None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(DEFAULT_LEVEL)

        # 文件日志
        self.setup_file_logging(name, mode)
        
        # BetterStack日志
        if betterstack_token:
            self.setup_betterstack_logging(name, betterstack_token)

        self.logger.info(f"LogWrapper initialized for {name}")

    def setup_betterstack_logging(self, name, token):
        betterstack_handler = LogtailHandler(source_token=token)
        formatter = logging.Formatter(LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
        betterstack_handler.setFormatter(formatter)
        self.logger.addHandler(betterstack_handler)
        self.logger.info("BetterStack Logging enabled")

    def setup_file_logging(self, name, mode):
        self.create_directory()
        self.filename = f"{LogWrapper.PATH}/{name}.log"
        file_handler = logging.FileHandler(self.filename, mode=mode)
        formatter = logging.Formatter(LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def create_directory(self):
        if not os.path.exists(LogWrapper.PATH):
            os.makedirs(LogWrapper.PATH)
