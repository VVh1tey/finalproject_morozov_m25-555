import hashlib
import uuid
from datetime import datetime
from typing import Dict

from valutatrade_hub.core.currencies import Currency, get_currency
from valutatrade_hub.core.exceptions import InsufficientFundsError

class User:
    """Класс User представляет пользователя системы."""

    def __init__(self, user_id: int, username: str, hashed_password: str, salt: str, registration_date: datetime):
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        if not value:
            raise ValueError("Имя пользователя не может быть пустым.")
        self._username = value

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def get_user_info(self) -> dict:
        """Возвращает информацию о пользователе (без пароля)."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "registration_date": self.registration_date.isoformat()
        }

    def change_password(self, new_password: str):
        """Изменяет пароль пользователя, хешируя новый пароль."""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов.")
        self._salt = uuid.uuid4().hex
        self._hashed_password = hashlib.sha256(f"{new_password}{self._salt}".encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Проверяет введенный пароль на совпадение."""
        return self._hashed_password == hashlib.sha256(f"{password}{self._salt}".encode()).hexdigest()


class Wallet:
    """Класс Wallet представляет кошелек пользователя для одной конкретной валюты."""

    def __init__(self, currency: Currency, balance: float = 0.0):
        self._currency = currency
        self.balance = balance  # Используем сеттер при инициализации

    @property
    def currency(self) -> Currency:
        return self._currency

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float):
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError("Баланс не может быть отрицательным и должен быть числом.")
        self._balance = value

    def deposit(self, amount: float):
        """Пополняет баланс кошелька."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительным числом.")
        self.balance += amount

    def withdraw(self, amount: float):
        """Снимает средства с баланса кошелька."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Сумма снятия должна быть положительным числом.")
        if amount > self.balance:
            raise InsufficientFundsError(code=self.currency.code, available=self.balance, required=amount)
        self.balance -= amount


class Portfolio:
    """Класс Portfolio управляет всеми кошельками одного пользователя."""

    def __init__(self, user_id: int, wallets: Dict[str, Wallet] = None):
        self._user_id = user_id
        self._wallets = wallets if wallets is not None else {}

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> Dict[str, Wallet]:
        return self._wallets.copy()

    def add_wallet(self, currency_code: str) -> Wallet:
        """Добавляет новый кошелек в портфель, если его еще нет."""
        if currency_code in self._wallets:
            raise ValueError(f"Кошелек для валюты '{currency_code}' уже существует.")
        
        currency = get_currency(currency_code)
        wallet = Wallet(currency=currency)
        self._wallets[currency_code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает кошелек по коду валюты."""
        wallet = self._wallets.get(currency_code)
        if not wallet:
            raise ValueError(f"Кошелек для валюты '{currency_code}' не найден.")
        return wallet
