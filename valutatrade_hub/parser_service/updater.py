import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service import storage

logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    """Структура для хранения результата обновления от одного источника."""
    source_name: str
    rates_count: int
    duration_ms: float


class RatesUpdater:
    """Координирует процесс обновления курсов валют."""

    def __init__(self, clients: Optional[List[BaseApiClient]] = None):
        if clients is None:
            self.clients = {
                "coingecko": CoinGeckoClient(),
                "exchangerate": ExchangeRateApiClient(),
            }
        else:
            self.clients = {client.__class__.__name__.lower(): client for client in clients}

    def run_update(self, source: Optional[str] = None) -> Tuple[List[UpdateResult], List[str]]:
        """
        Запускает обновление курсов.
        
        :param source: Источник для обновления ('coingecko' или 'exchangerate').
        :return: Кортеж (список успешных результатов, список ошибок).
        """
        all_rates: Dict[str, float] = {}
        all_sources: Dict[str, str] = {}
        results: List[UpdateResult] = []
        errors: List[str] = []

        clients_to_run = self.clients.items()
        if source:
            source = source.lower()
            if source not in self.clients:
                raise ValueError(f"Неизвестный источник: {source}")
            clients_to_run = [(source, self.clients[source])]

        for name, client in clients_to_run:
            try:
                logger.info(f"Fetching rates from {name}...")
                start_time = time.perf_counter()
                rates = client.fetch_rates()
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000

                all_rates.update(rates)
                for pair in rates:
                    all_sources[pair] = name
                
                results.append(UpdateResult(
                    source_name=name,
                    rates_count=len(rates),
                    duration_ms=duration_ms
                ))
                logger.info(f"Successfully fetched {len(rates)} rates from {name} in {duration_ms:.2f}ms.")
            except ApiRequestError as e:
                error_msg = f"Failed to fetch from {name}: {e.reason}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        if all_rates:
            # Обновляем исторические данные и snapshot
            for pair, rate in all_rates.items():
                from_curr, to_curr = pair.split('_')
                storage.save_rate_to_history(
                    from_currency=from_curr,
                    to_currency=to_curr,
                    rate=rate,
                    source=all_sources[pair]
                )
            storage.update_rates_snapshot(all_rates, all_sources)
        
        return results, errors
