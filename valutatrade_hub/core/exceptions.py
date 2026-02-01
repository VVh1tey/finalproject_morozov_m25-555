"""Модуль с кастомными исключениями."""


class ApiRequestError(Exception):
    """Ошибка при запросе к API."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class CurrencyNotFoundError(Exception):
    """Валюта не найдена."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class InsufficientFundsError(Exception):
    """Недостаточно средств на счете."""

    def __init__(self, code: str, available: float, required: float):
        self.code = code
        self.available = available
        self.required = required
        super().__init__(
            f"!! Недостаточно средств\n@ Доступно: {available:.2f} {code}\nТребуется: {required:.2f} {code}"
        )


class RateNotFoundError(Exception):
    """Курс валюты не найден."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Курс для '{code}' не найден.")
