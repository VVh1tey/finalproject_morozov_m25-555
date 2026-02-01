import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import settings

def setup_logging():
    """
    Настраивает систему логирования.
    """
    log_file_path = Path(settings.get("LOGS_FILE"))
    log_format = settings.get("LOG_FORMAT")
    
    # Создаем директорию для логов, если она не существует
    log_file_path.parent.mkdir(exist_ok=True)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) #NOTE: ПОСТАВИТЬ НА ERROR ПОТОМ

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=2
    )
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    
    root_logger.addHandler(file_handler)
