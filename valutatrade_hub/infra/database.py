import json
from pathlib import Path
from typing import List, Dict, Any

from valutatrade_hub.infra.settings import settings

class DatabaseManager:
    """
    Singleton для управления доступом к данным в JSON-файлах.
    Абстрагирует чтение и запись, используя пути из SettingsLoader.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._init_paths()
        return cls._instance

    def _init_paths(self):
        """Инициализирует пути к файлам данных."""
        self.users_path = Path(settings.get("USERS_FILE"))
        self.portfolios_path = Path(settings.get("PORTFOLIOS_FILE"))
        self.rates_path = Path(settings.get("RATES_FILE"))
        self.exchange_rates_path = Path(settings.get("HISTORY_FILE_PATH", "data/exchange_rates.json"))
        
        # Убедимся, что директория data существует
        self.users_path.parent.mkdir(exist_ok=True)


    def read(self, table: str) -> List[Dict[str, Any]]:
        """Читает данные из указанной таблицы (JSON-файла)."""
        path = self._get_path(table)
        if not path.exists():
            # Если файл не существует, создаем его с пустым списком или словарем
            default_content = [] if table != 'rates' else {}
            self.write(table, default_content)
            return default_content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return [] if table != 'rates' else {}

    def write(self, table: str, data: Any):
        """Записывает данные в указанную таблицу (JSON-файл)."""
        path = self._get_path(table)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _get_path(self, table: str) -> Path:
        """Возвращает путь к файлу по имени таблицы."""
        if table == 'users':
            return self.users_path
        elif table == 'portfolios':
            return self.portfolios_path
        elif table == 'rates':
            return self.rates_path
        elif table == 'exchange_rates':
            return self.exchange_rates_path
        else:
            raise ValueError(f"Неизвестная таблица: {table}")

db_manager = DatabaseManager()
