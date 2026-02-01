import logging
from datetime import datetime
from typing import Dict, Any

from valutatrade_hub.infra.database import db_manager

logger = logging.getLogger(__name__)

def save_rate_to_history(from_currency: str, to_currency: str, rate: float, source: str):
    """
    Сохраняет одну запись о курсе в исторический файл.
    """
    history = db_manager.read('exchange_rates')
    timestamp = datetime.utcnow().isoformat()
    
    record = {
        "id": f"{from_currency}_{to_currency}_{timestamp}",
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": rate,
        "timestamp": timestamp,
        "source": source
    }
    history.append(record)
    db_manager.write('exchange_rates', history)
    logger.debug(f"Saved rate to history: {record['id']}")


def update_rates_snapshot(rates_data: Dict[str, float], sources: Dict[str, str]):
    """
    Обновляет файл последними актуальными курсами.
    """
    try:
        snapshot = db_manager.read('rates')
        if not isinstance(snapshot, dict) or 'pairs' not in snapshot:
            snapshot = {'pairs': {}}
    except Exception:
        snapshot = {'pairs': {}}

    now = datetime.utcnow().isoformat()
    
    for pair, rate in rates_data.items():
        source = sources.get(pair, "Unknown")
        snapshot['pairs'][pair] = {
            "rate": rate,
            "updated_at": now,
            "source": source
        }

    snapshot['last_refresh'] = now
    db_manager.write('rates', snapshot)
    logger.info(f"Updated rates snapshot with {len(rates_data)} pairs.")
