import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict

import requests
from requests.exceptions import RequestException

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import parser_config

logger = logging.getLogger(__name__)

class BaseApiClient(ABC):
    """Абстрактный базовый класс для клиентов API курсов валют."""

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы валют и возвращает их в стандартизированном формате.
        Формат: {"BTC_USD": 60000.0, "EUR_USD": 1.1}
        """
        pass

class CoinGeckoClient(BaseApiClient):
    """Клиент для API CoinGecko."""

    def fetch_rates(self) -> Dict[str, float]:
        ids = ",".join(parser_config.CRYPTO_ID_MAP.values())
        params = {
            "ids": ids,
            "vs_currencies": parser_config.BASE_CURRENCY.lower()
        }
        try:
            response = requests.get(
                parser_config.COINGECKO_URL,
                params=params,
                timeout=parser_config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(f"CoinGecko response: {data}")

            rates = {}
            for ticker, coingecko_id in parser_config.CRYPTO_ID_MAP.items():
                if coingecko_id in data:
                    rate = data[coingecko_id][parser_config.BASE_CURRENCY.lower()]
                    rates[f"{ticker}_{parser_config.BASE_CURRENCY}"] = float(rate)
            return rates

        except RequestException as e:
            logger.error(f"CoinGecko API request failed: {e}")
            raise ApiRequestError(reason=f"Network error accessing CoinGecko: {e}")
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse CoinGecko response: {e}")
            raise ApiRequestError(reason=f"Invalid response format from CoinGecko: {e}")

class ExchangeRateApiClient(BaseApiClient):
    """Клиент для ExchangeRate-API."""

    def fetch_rates(self) -> Dict[str, float]:
        api_key = parser_config.EXCHANGERATE_API_KEY
        if not api_key:
            raise ApiRequestError(reason="ExchangeRate-API key is not configured.")
            
        url = f"{parser_config.EXCHANGERATE_API_URL}/{api_key}/latest/{parser_config.BASE_CURRENCY}"
        
        try:
            response = requests.get(url, timeout=parser_config.REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"ExchangeRate-API response: {data}")

            if data.get("result") != "success":
                raise ApiRequestError(reason=f"ExchangeRate-API returned an error: {data.get('error-type')}")

            rates = {}
            conversion_rates = data.get("conversion_rates", {})
            for ticker in parser_config.FIAT_CURRENCIES:
                if ticker in conversion_rates:
                    rate_vs_base = conversion_rates[ticker]
                    rates[f"{ticker}_{parser_config.BASE_CURRENCY}"] = float(rate_vs_base)
            
            return rates

        except RequestException as e:
            logger.error(f"ExchangeRate-API request failed: {e}")
            raise ApiRequestError(reason=f"Network error accessing ExchangeRate-API: {e}")
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse ExchangeRate-API response: {e}")
            raise ApiRequestError(reason=f"Invalid response format from ExchangeRate-API: {e}")
