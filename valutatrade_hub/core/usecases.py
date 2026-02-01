from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import get_currency, CurrencyNotFoundError
from valutatrade_hub.core.exceptions import RateNotFoundError, ApiRequestError
from valutatrade_hub.core.models import User, Portfolio, Wallet
from valutatrade_hub.core.utils import hash_password, verify_password
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import db_manager
from valutatrade_hub.infra.settings import settings
from valutatrade_hub.parser_service.updater import RatesUpdater


SESSION: Dict[str, Any] = {"current_user": None}

@log_action("REGISTER")
def register(username: str, password: str) -> str:
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов.")
    users = db_manager.read('users')
    if any(user['username'] == username for user in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято.")
    user_id = (max(u['user_id'] for u in users) + 1) if users else 1
    hashed_pass, salt = hash_password(password)
    users.append({
        "user_id": user_id, "username": username, "hashed_password": hashed_pass,
        "salt": salt, "registration_date": datetime.now().isoformat()
    })
    db_manager.write('users', users)
    portfolios = db_manager.read('portfolios')
    portfolios.append({"user_id": user_id, "wallets": {}})
    db_manager.write('portfolios', portfolios)
    return f"Пользователь '{username}' зарегистрирован (id={user_id})."

@log_action("LOGIN")
def login(username: str, password: str) -> str:
    user_data = next((u for u in db_manager.read('users') if u['username'] == username), None)
    if not user_data or not verify_password(password, user_data['salt'], user_data['hashed_password']):
        raise ValueError("Неверное имя пользователя или пароль.")
    SESSION["current_user"] = User(
        user_id=user_data['user_id'], username=user_data['username'],
        hashed_password=user_data['hashed_password'], salt=user_data['salt'],
        registration_date=datetime.fromisoformat(user_data['registration_date'])
    )
    return f"Вы вошли как '{username}'"

def get_current_user() -> Optional[User]:
    return SESSION.get("current_user")

def _load_portfolio(user: User) -> Portfolio:
    portfolios_data = db_manager.read('portfolios')
    user_portfolio_data = next((p for p in portfolios_data if p.get('user_id') == user.user_id), None)
    wallets = {}
    if user_portfolio_data and 'wallets' in user_portfolio_data:
        for code, data in user_portfolio_data['wallets'].items():
            try:
                wallets[code] = Wallet(currency=get_currency(code), balance=data.get('balance', 0.0))
            except CurrencyNotFoundError:
                continue
    return Portfolio(user_id=user.user_id, wallets=wallets)

def _save_portfolio(portfolio: Portfolio):
    portfolios_data = db_manager.read('portfolios')
    user_portfolio_data = next((p for p in portfolios_data if p.get('user_id') == portfolio.user_id), None)
    serialized_wallets = {code: {"balance": w.balance} for code, w in portfolio.wallets.items()}
    if user_portfolio_data:
        user_portfolio_data['wallets'] = serialized_wallets
    else:
        portfolios_data.append({"user_id": portfolio.user_id, "wallets": serialized_wallets})
    db_manager.write('portfolios', portfolios_data)

def show_portfolio(base: Optional[str] = None) -> str:
    user = get_current_user()
    if not user: raise PermissionError("Сначала выполните login.")
    base_code = base or settings.get("DEFAULT_BASE_CURRENCY")
    get_currency(base_code)
    portfolio = _load_portfolio(user)
    if not portfolio.wallets: return "Ваш портфель пуст."
    
    rates_snapshot = db_manager.read('rates')
    rates = rates_snapshot.get('pairs', {})
    
    table = PrettyTable()
    table.field_names = ["Валюта", "Баланс", f"Стоимость в {base_code}"]
    total_value = 0
    for code, wallet in portfolio.wallets.items():
        rate = 1.0 if code == base_code else rates.get(f"{code}_{base_code}", {}).get('rate')
        value_str = f"{wallet.balance * rate:.2f} {base_code}" if rate else "Курс не найден"
        if rate: total_value += wallet.balance * rate
        table.add_row([code, f"{wallet.balance:.4f}", value_str])
        
    header = f"Портфель пользователя '{user.username}' (база: {base_code}):\n"
    footer = f"\n---------------------------------\nИТОГО: {total_value:.2f} {base_code}"
    return header + table.get_string() + footer

@log_action("BUY")
def buy(currency: str, amount: float) -> str:
    if amount <= 0: raise ValueError("'amount' должен быть положительным числом.")
    user = get_current_user()
    if not user: raise PermissionError("Сначала выполните login.")
    
    currency_to_buy = get_currency(currency)
    base_currency_code = settings.get("DEFAULT_BASE_CURRENCY")
    
    portfolio = _load_portfolio(user)

    # Если покупаем базовую валюту, просто пополняем баланс
    if currency_to_buy.code == base_currency_code:
        wallet = portfolio.get_wallet(base_currency_code) if base_currency_code in portfolio.wallets else portfolio.add_wallet(base_currency_code)
        wallet.deposit(amount)
        _save_portfolio(portfolio)
        return f"↑ Пополнено {amount:.2f} {base_currency_code}"

    # Логика покупки за базовую валюту
    rates_snapshot = db_manager.read('rates')
    pair_key = f"{currency_to_buy.code}_{base_currency_code}"
    rate_info = rates_snapshot.get('pairs', {}).get(pair_key)
    
    if not rate_info:
        raise RateNotFoundError(code=pair_key)
        
    cost = amount * rate_info['rate']
    
    try:
        base_wallet = portfolio.get_wallet(base_currency_code)
    except ValueError:
        raise InsufficientFundsError(code=base_currency_code, available=0.0, required=cost)

    base_wallet.withdraw(cost)
    
    target_wallet = portfolio.get_wallet(currency_to_buy.code) if currency_to_buy.code in portfolio.wallets else portfolio.add_wallet(currency_to_buy.code)
    target_wallet.deposit(amount)
    
    _save_portfolio(portfolio)
    
    return (f"✓ Покупка выполнена: {amount:.4f} {currency_to_buy.code}\n"
            f"↓ Списано: {cost:.2f} {base_currency_code}")

@log_action("SELL")
def sell(currency: str, amount: float) -> str:
    if amount <= 0: raise ValueError("'amount' должен быть положительным числом.")
    user = get_current_user()
    if not user: raise PermissionError("Сначала выполните login.")
    portfolio = _load_portfolio(user)
    wallet = portfolio.get_wallet(currency)
    old_balance = wallet.balance
    wallet.withdraw(amount)
    _save_portfolio(portfolio)
    return f"Продажа выполнена: {amount:.4f} {currency}\n- {currency}: было {old_balance:.4f} → стало {wallet.balance:.4f}"

def get_rate(from_currency: str, to_currency: str) -> str:
    get_currency(from_currency); get_currency(to_currency)
    rates_data = db_manager.read('rates')
    ttl = timedelta(seconds=settings.get("RATES_TTL_SECONDS"))
    last_refresh = rates_data.get("last_refresh")
    if not last_refresh or datetime.fromisoformat(last_refresh) + ttl < datetime.now():
        raise ApiRequestError(reason="Кэш курсов устарел. Выполните 'update-rates'.")
    
    pair = f"{from_currency}_{to_currency}"
    rates = rates_data.get('pairs', {})
    rate_info = rates.get(pair) or rates.get(f"{to_currency}_{from_currency}")
    
    if not rate_info: raise RateNotFoundError(code=pair)

    rate = rate_info['rate'] if pair in rates else 1 / rate_info['rate']
    rev_rate = 1 / rate
    return (f"⇄ КУРС ВАЛЮТ\n"
            f"• {from_currency} → {to_currency}: {rate:.8f}\n"
            f"• {to_currency} → {from_currency}: {rev_rate:.8f}\n"
            f"◴ Обновлено: {rate_info['updated_at']}")

@log_action("UPDATE_RATES")
def update_rates(source: Optional[str] = None) -> str:
    output_lines = ["⧗ Начало обновления курсов..."]
    updater = RatesUpdater()
    results, errors = updater.run_update(source)

    total_rates = 0
    for res in results:
        total_rates += res.rates_count
        output_lines.append(
            f"  [✓] {res.source_name}: получено {res.rates_count} курсов за {res.duration_ms:.2f} мс"
        )
    
    if errors:
        for error in errors:
            output_lines.append(f"  [!!] {error}")
        output_lines.append("\nОбновление завершено с ошибками.")
    else:
        output_lines.append(f"\n✓ Обновление курсов успешно завершено!")
    
    output_lines.append(f"Σ Всего обновлено курсов: {total_rates}")
    output_lines.append(f"◴ Время обновления: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(output_lines)

def show_rates(currency: Optional[str] = None, top: Optional[int] = None) -> str:
    rates_data = db_manager.read('rates')
    if not rates_data or not rates_data.get('pairs'):
        return "Локальный кеш курсов пуст. Выполните 'update-rates'."
    
    rates = rates_data['pairs'].items()
    if currency:
        rates = [r for r in rates if currency.upper() in r[0].split('_')]
    
    if not rates:
        return f"Курс для '{currency}' не найден в кеше."

    if top:
        rates = sorted(rates, key=lambda item: item[1]['rate'], reverse=True)[:top]

    table = PrettyTable()
    table.field_names = ["Пара", "Курс", "Источник", "Обновлено"]
    for pair, info in rates:
        table.add_row([pair, f"{info['rate']:.4f}", info['source'], info['updated_at']])
    
    return f"Курсы из кеша (обновлено: {rates_data['last_refresh']}):\n" + table.get_string()
