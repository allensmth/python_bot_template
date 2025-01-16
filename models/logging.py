from dataclasses import dataclass
from typing import Optional
from logtail import LogtailHandler
import logging

@dataclass
class Logging:
    name: str
    log_file_path: str
    betterstack_token: Optional[str] = None
    
    def __post_init__(self):
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)
        
        # 文件日志
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        
        # BetterStack日志
        if self.betterstack_token:
            betterstack_handler = LogtailHandler(source_token=self.betterstack_token)
            self.logger.addHandler(betterstack_handler)

@dataclass
class CloudLogging:
    enabled: bool
    betterstack_token: Optional[str] = None

@dataclass
class LoggingConfig:
    directories: dict
    cloud_logging: Optional[CloudLogging]