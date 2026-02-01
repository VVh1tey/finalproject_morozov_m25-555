import json
import hashlib
import uuid
from pathlib import Path
from typing import List, Dict, Any

DATA_PATH = Path(__file__).parent.parent.parent / "data"
USERS_FILE = DATA_PATH / "users.json"
PORTFOLIOS_FILE = DATA_PATH / "portfolios.json"
RATES_FILE = DATA_PATH / "rates.json"


def read_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """Читает данные из JSON-файла."""
    if not file_path.exists():
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json_file(file_path: Path, data: List[Dict[str, Any]]):
    """Записывает данные в JSON-файл."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def hash_password(password: str) -> tuple[str, str]:
    """Хеширует пароль с использованием соли."""
    salt = uuid.uuid4().hex
    hashed_password = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    return hashed_password, salt


def verify_password(password: str, salt: str, hashed_password: str) -> bool:
    """Проверяет пароль."""
    return hashed_password == hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
