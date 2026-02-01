import hashlib
import uuid
from datetime import datetime
from typing import Dict


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
            raise ValueError("Имя не может быть пустым.")
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
        """Изменяет пароль пользователя, с хешированием нового пароля."""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов.")
        self._salt = uuid.uuid4().hex
        self._hashed_password = hashlib.sha256(f"{new_password}{self._salt}".encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль на совпадение."""
        return self._hashed_password == hashlib.sha256(f"{password}{self._salt}".encode()).hexdigest()


class Wallet:
    """Класс Wallet представляет кошелёк пользователя для одной конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self._balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float):
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError("Баланс не может быть отрицательным и должен быть числом.")
        self._balance = value

    def deposit(self, amount: float):
        """Пополнение баланса."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительным числом.")
        self.balance += amount

    def withdraw(self, amount: float):
        """Снятие средств."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Сумма снятия должна быть положительным числом.")
        if amount > self.balance:
            raise ValueError("Недостаточно средств.")
        self.balance -= amount

    def get_balance_info(self) -> dict:
        """Вывод информации о текущем балансе."""
        return {"currency_code": self.currency_code, "balance": self.balance}


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

    def add_currency(self, currency_code: str):
        """Добавляет новый кошелёк в портфель."""
        if currency_code in self._wallets:
            raise ValueError(f"Кошелек для {currency_code} уже существует.")
        self._wallets[currency_code] = Wallet(currency_code)

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает объект Wallet по коду валюты."""
        if currency_code not in self._wallets:
            raise ValueError(f"Кошелек для {currency_code} не найден.")
        return self._wallets[currency_code]

    def get_total_value(self, base_currency: str = 'USD') -> float:
        """Возвращает общую стоимость всех валют пользователя в указанной базовой валюте."""
        # Фиктивные данные для курсов, пока не подключен Parser Service
        exchange_rates = {
            "USD": 1.0,
            "BTC": 60000.0,
            "EUR": 1.1,
            "ETH": 3000.0,
            "RUB": 0.01
        }
        total_value = 0.0
        for currency_code, wallet in self._wallets.items():
            rate = exchange_rates.get(currency_code, 0)
            total_value += wallet.balance * rate
        return total_value
