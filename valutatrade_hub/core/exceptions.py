"""Модуль с кастомными исключениями."""

class ApiRequestError(Exception):
    """Ошибка при запросе к API."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"API request failed: {reason}")

class CurrencyNotFoundError(Exception):
    """Валюта не найдена."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Currency '{code}' not found.")

class InsufficientFundsError(Exception):
    """Недостаточно средств на счете."""
    def __init__(self, code: str, available: float, required: float):
        self.code = code
        self.available = available
        self.required = required
        super().__init__(f"Insufficient funds for {code}. Available: {available}, Required: {required}")

class RateNotFoundError(Exception):
    """Курс валюты не найден."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Rate for '{code}' not found.")
