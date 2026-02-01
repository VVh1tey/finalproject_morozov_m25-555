import hashlib
import re
import uuid


def hash_password(password: str) -> tuple[str, str]:
    """Хеширует пароль с использованием соли."""
    salt = uuid.uuid4().hex
    hashed_password = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    return hashed_password, salt


def verify_password(password: str, salt: str, hashed_password: str) -> bool:
    """Проверяет пароль."""
    return hashed_password == hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def is_valid_currency_code(code: str) -> bool:
    """
    Проверяет, что код валюты соответствует формату:
    - Верхний регистр
    - 2-5 символов
    - Без пробелов
    """
    if not isinstance(code, str):
        return False
    return bool(re.match(r"^[A-Z]{2,5}$", code))
