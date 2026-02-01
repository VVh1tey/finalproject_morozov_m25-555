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

# Простая "сессия" для хранения залогиненного пользователя
SESSION: Dict[str, Any] = {"current_user": None}


@log_action("REGISTER")
def register(username: str, password: str) -> str:
    """Регистрирует нового пользователя."""
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов.")

    users = db_manager.read('users')
    if any(user['username'] == username for user in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято.")

    user_id = len(users) + 1 if users else 1
    hashed_pass, salt = hash_password(password)
    
    new_user_data = {
        "user_id": user_id,
        "username": username,
        "hashed_password": hashed_pass,
        "salt": salt,
        "registration_date": datetime.now().isoformat()
    }
    users.append(new_user_data)
    db_manager.write('users', users)

    # Создание пустого портфеля
    portfolios = db_manager.read('portfolios')
    portfolios.append({"user_id": user_id, "wallets": {}})
    db_manager.write('portfolios', portfolios)

    return f"Пользователь '{username}' зарегистрирован (id={user_id})."


@log_action("LOGIN")
def login(username: str, password: str) -> str:
    """Аутентифицирует пользователя и сохраняет сессию."""
    users = db_manager.read('users')
    user_data = next((user for user in users if user['username'] == username), None)

    if not user_data:
        raise ValueError(f"Пользователь '{username}' не найден.")

    if not verify_password(password, user_data['salt'], user_data['hashed_password']):
        raise ValueError("Неверный пароль.")

    user = User(
        user_id=user_data['user_id'],
        username=user_data['username'],
        hashed_password=user_data['hashed_password'],
        salt=user_data['salt'],
        registration_date=datetime.fromisoformat(user_data['registration_date'])
    )
    SESSION["current_user"] = user
    return f"Вы вошли как '{user.username}'"


def get_current_user() -> Optional[User]:
    """Возвращает текущего залогиненного пользователя."""
    return SESSION.get("current_user")


def _load_portfolio(user: User) -> Portfolio:
    """Загружает портфель пользователя из базы данных."""
    portfolios_data = db_manager.read('portfolios')
    user_portfolio_data = next((p for p in portfolios_data if p.get('user_id') == user.user_id), None)

    wallets = {}
    if user_portfolio_data and 'wallets' in user_portfolio_data:
        for code, data in user_portfolio_data['wallets'].items():
            try:
                currency = get_currency(code)
                wallets[code] = Wallet(currency=currency, balance=data.get('balance', 0.0))
            except CurrencyNotFoundError:
                # Игнорируем некорректные кошельки в данных
                continue
    
    return Portfolio(user_id=user.user_id, wallets=wallets)


def _save_portfolio(portfolio: Portfolio):
    """Сохраняет портфель пользователя в базу данных."""
    portfolios_data = db_manager.read('portfolios')
    user_portfolio_data = next((p for p in portfolios_data if p.get('user_id') == portfolio.user_id), None)

    serialized_wallets = {
        code: {"balance": wallet.balance} for code, wallet in portfolio.wallets.items()
    }

    if user_portfolio_data:
        user_portfolio_data['wallets'] = serialized_wallets
    else:
        portfolios_data.append({"user_id": portfolio.user_id, "wallets": serialized_wallets})
    
    db_manager.write('portfolios', portfolios_data)


def show_portfolio(base: Optional[str] = None) -> str:
    """Показывает портфель текущего пользователя."""
    current_user = get_current_user()
    if not current_user:
        raise PermissionError("Сначала выполните login.")

    base_currency_code = base or settings.get("DEFAULT_BASE_CURRENCY")
    get_currency(base_currency_code) # Проверка, что базовая валюта существует

    portfolio = _load_portfolio(current_user)

    if not portfolio.wallets:
        return "Ваш портфель пуст."
        
    rates = db_manager.read('rates')
    # TODO: Implement rates fetching logic with
    
    table = PrettyTable()
    table.field_names = ["Валюта", "Баланс", f"Стоимость в {base_currency_code}"]
    total_value = 0
    
    for code, wallet in portfolio.wallets.items():
        if code == base_currency_code:
            rate = 1.0
        else:
            pair = f"{code}_{base_currency_code}"
            reverse_pair = f"{base_currency_code}_{code}"
            if pair in rates:
                 rate = rates[pair]['rate']
            elif reverse_pair in rates:
                 rate = 1 / rates[reverse_pair]['rate']
            else:
                rate = None

        if rate is None:
            value_in_base_str = "Курс не найден"
        else:
            value_in_base = wallet.balance * rate
            total_value += value_in_base
            value_in_base_str = f"{value_in_base:.2f} {base_currency_code}"

        table.add_row([code, f"{wallet.balance:.4f}", value_in_base_str])

    header = f"Портфель пользователя '{current_user.username}' (база: {base_currency_code}):\n"
    footer = f"\n---------------------------------\nИТОГО: {total_value:.2f} {base_currency_code}"
    return header + table.get_string() + footer


@log_action("BUY")
def buy(currency: str, amount: float) -> str:
    """Покупает валюту для текущего пользователя."""
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом.")

    current_user = get_current_user()
    if not current_user:
        raise PermissionError("Сначала выполните login.")

    get_currency(currency) # Проверка существования валюты
    portfolio = _load_portfolio(current_user)
    
    try:
        wallet = portfolio.get_wallet(currency)
        old_balance = wallet.balance
        wallet.deposit(amount)
    except ValueError: # Кошелек не найден
        wallet = portfolio.add_wallet(currency)
        old_balance = 0.0
        wallet.deposit(amount)

    _save_portfolio(portfolio)
    
    return (f"Покупка выполнена: {amount:.4f} {currency}\n"
            f"Изменения в портфеле:\n"
            f"- {currency}: было {old_balance:.4f} → стало {wallet.balance:.4f}")


@log_action("SELL")
def sell(currency: str, amount: float) -> str:
    """Продает валюту для текущего пользователя."""
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом.")

    current_user = get_current_user()
    if not current_user:
        raise PermissionError("Сначала выполните login.")

    get_currency(currency) # Проверка существования валюты
    portfolio = _load_portfolio(current_user)
    
    wallet = portfolio.get_wallet(currency) # ValueError если кошелька нет
    old_balance = wallet.balance
    wallet.withdraw(amount) # InsufficientFundsError если не хватает

    _save_portfolio(portfolio)
    
    return (f"Продажа выполнена: {amount:.4f} {currency}\n"
            f"Изменения в портфеле:\n"
            f"- {currency}: было {old_balance:.4f} → стало {wallet.balance:.4f}")


def get_rate(from_currency: str, to_currency: str) -> str:
    """Получает курс валюты."""
    get_currency(from_currency)
    get_currency(to_currency)

    rates_data = db_manager.read('rates')
    ttl = timedelta(seconds=settings.get("RATES_TTL_SECONDS"))
    
    last_refresh_str = rates_data.get("last_refresh")
    if not last_refresh_str or datetime.fromisoformat(last_refresh_str) + ttl < datetime.now():
        #TODO: Implement Parser Service integration
        raise ApiRequestError(reason="Кэш курсов устарел, а сервис обновления не реализован.")

    pair = f"{from_currency}_{to_currency}"
    reverse_pair = f"{to_currency}_{from_currency}"

    rate = None
    updated_at = "N/A"
    
    if pair in rates_data:
        rate_info = rates_data[pair]
        rate = rate_info['rate']
        updated_at = rate_info['updated_at']
    elif reverse_pair in rates_data:
        rate_info = rates_data[reverse_pair]
        rate = 1 / rate_info['rate']
        updated_at = rate_info['updated_at']
    else:
        raise RateNotFoundError(code=f"{from_currency}→{to_currency}")

    reverse_rate = 1 / rate
    
    return (f"Курс {from_currency}→{to_currency}: {rate:.8f} (обновлено: {updated_at})\n"
            f"Обратный курс {to_currency}→{from_currency}: {reverse_rate:.8f}")

@log_action("UPDATE_RATES")
def update_rates(source: Optional[str] = None) -> str:
    """Обновляет курсы валют (заглушка)."""
    #TODO: Implement Parser Service integration
    raise ApiRequestError(reason="Сервис обновления курсов не реализован.")

def show_rates(currency: Optional[str] = None, top: Optional[int] = None) -> str:
    """Показывает курсы валют (заглушка)."""
    return "Просмотр курсов пока не реализован."
