from typing import Any


class SettingsLoader:
    """
    Singleton для загрузки и предоставления настроек проекта.
    """

    _instance = None
    _settings = {
        "DATA_PATH": "data/",
        "USERS_FILE": "data/users.json",
        "PORTFOLIOS_FILE": "data/portfolios.json",
        "RATES_FILE": "data/rates.json",
        "LOGS_PATH": "logs/",
        "LOGS_FILE": "logs/actions.log",
        "LOG_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "RATES_TTL_SECONDS": 300,
        "DEFAULT_BASE_CURRENCY": "USD",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
        return cls._instance

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки по ключу."""
        return self._settings.get(key, default)


settings = SettingsLoader()
