import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import settings

def setup_logging():
    """Настраивает систему логирования."""
    log_file_path = Path(settings.get("LOGS_FILE"))
    log_format = settings.get("LOG_FORMAT")
    
    # Создаем директорию для логов, если она не существует
    log_file_path.parent.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            RotatingFileHandler(
                log_file_path,
                maxBytes=5*1024*1024,  # 5 MB
                backupCount=2
            )
            # StreamHandler убран, чтобы логи не дублировались в консоль
        ]
    )
