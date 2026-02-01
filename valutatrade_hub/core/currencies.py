from abc import ABC, abstractmethod
from typing import Dict

from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.utils import is_valid_currency_code


class Currency(ABC):
    """Абстрактный базовый класс для всех валют."""

    def __init__(self, name: str, code: str):
        if not name:
            raise ValueError("Имя валюты не может быть пустым.")
        if not is_valid_currency_code(code):
            raise ValueError(f"Некорректный код валюты: {code}")
        self.name = name
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает строковое представление для UI/логов."""
        pass


class FiatCurrency(Currency):
    """Представляет фиатную валюту."""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Представляет криптовалюту."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"


# Временный реестр доступных валют
_currency_registry: Dict[str, Currency] = {
    "USD": FiatCurrency(name="US Dollar", code="USD", issuing_country="United States"),
    "EUR": FiatCurrency(name="Euro", code="EUR", issuing_country="Eurozone"),
    "RUB": FiatCurrency(name="Russian Ruble", code="RUB", issuing_country="Russia"),
    "BTC": CryptoCurrency(
        name="Bitcoin", code="BTC", algorithm="SHA-256", market_cap=1.12e12
    ),
    "ETH": CryptoCurrency(
        name="Ethereum", code="ETH", algorithm="Ethash", market_cap=3.5e11
    ),
}


def get_currency(code: str) -> Currency:
    """
    Функция для получения экземпляра валюты по её коду.
    """
    if not is_valid_currency_code(code):
        raise CurrencyNotFoundError(code=code)

    currency = _currency_registry.get(code.upper())
    if currency is None:
        raise CurrencyNotFoundError(code=code)
    return currency


def get_all_currencies_info() -> str:
    """Возвращает информацию о всех валютах в реестре."""
    return "\n".join(
        [currency.get_display_info() for currency in _currency_registry.values()]
    )
