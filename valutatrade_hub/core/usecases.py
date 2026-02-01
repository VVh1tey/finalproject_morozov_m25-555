from datetime import datetime
from typing import Dict, Any, Optional

from prettytable import PrettyTable

from valutatrade_hub.core.exceptions import InsufficientFundsError, RateNotFoundError
from valutatrade_hub.core.models import User, Portfolio, Wallet
from valutatrade_hub.core.utils import (
    read_json_file,
    write_json_file,
    hash_password,
    verify_password,
    USERS_FILE,
    PORTFOLIOS_FILE,
    RATES_FILE,
)

# Простая внутрипроцессная "сессия" для хранения залогиненного пользователя
SESSION: Dict[str, Any] = {"current_user": None}


def register(username: str, password: str) -> str:
    """Регистрирует нового пользователя."""
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов.")

    users = read_json_file(USERS_FILE)
    if any(user['username'] == username for user in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято.")

    user_id = len(users) + 1
    hashed_pass, salt = hash_password(password)
    registration_date = datetime.now()

    new_user = User(
        user_id=user_id,
        username=username,
        hashed_password=hashed_pass,
        salt=salt,
        registration_date=registration_date
    )

    users.append({
        "user_id": new_user.user_id,
        "username": new_user.username,
        "hashed_password": new_user.hashed_password,
        "salt": new_user.salt,
        "registration_date": new_user.registration_date.isoformat()
    })
    write_json_file(USERS_FILE, users)

    # Создание пустого портфеля
    portfolios = read_json_file(PORTFOLIOS_FILE)
    portfolios.append({"user_id": new_user.user_id, "wallets": {}})
    write_json_file(PORTFOLIOS_FILE, portfolios)

    return f"Пользователь '{new_user.username}' зарегистрирован (id={new_user.user_id})."


def login(username: str, password: str) -> str:
    """Аутентифицирует пользователя и сохраняет сессию."""
    users = read_json_file(USERS_FILE)
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


def show_portfolio(base: str = 'USD') -> str:
    """Показывает портфель текущего пользователя."""
    current_user = get_current_user()
    if not current_user:
        raise PermissionError("Сначала выполните login.")

    portfolios = read_json_file(PORTFOLIOS_FILE)
    user_portfolio_data = next((p for p in portfolios if p['user_id'] == current_user.user_id), None)

    if not user_portfolio_data or not user_portfolio_data.get('wallets'):
        return "Ваш портфель пуст."

    wallets = {
        code: Wallet(currency_code=code, balance=data.get('balance', 0.0))
        for code, data in user_portfolio_data.get('wallets', {}).items()
    }

    portfolio = Portfolio(user_id=current_user.user_id, wallets=wallets)

    # Заглушка для курсов валют
    rates_data = read_json_file(RATES_FILE)
    exchange_rates = {pair.split('_')[0]: data['rate'] for pair, data in rates_data.items() if pair.endswith(f"_{base}")}
    exchange_rates[base] = 1.0

    table = PrettyTable()
    table.field_names = ["Валюта", "Баланс", f"Стоимость в {base}"]
    total_value = 0
    
    for code, wallet in portfolio.wallets.items():
        rate = exchange_rates.get(code)
        if rate is None:
            value_in_base_str = "Курс не найден"
        else:
            value_in_base = wallet.balance * rate
            total_value += value_in_base
            value_in_base_str = f"{value_in_base:.2f} {base}"

        table.add_row([code, f"{wallet.balance:.4f}", value_in_base_str])

    header = f"Портфель пользователя '{current_user.username}' (база: {base}):\n"
    footer = f"\n---------------------------------\nИТОГО: {total_value:.2f} {base}"
    return header + table.get_string() + footer


def buy(currency: str, amount: float) -> str:
    """Покупка валюты."""
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом.")

    current_user = get_current_user()
    if not current_user:
        raise PermissionError("Сначала выполните login.")

    portfolios = read_json_file(PORTFOLIOS_FILE)
    user_portfolio_data = next((p for p in portfolios if p['user_id'] == current_user.user_id), None)
    
    if user_portfolio_data is None:
        user_portfolio_data = {"user_id": current_user.user_id, "wallets": {}}
        portfolios.append(user_portfolio_data)

    if currency not in user_portfolio_data['wallets']:
        user_portfolio_data['wallets'][currency] = {'balance': 0}
    
    old_balance = user_portfolio_data['wallets'][currency].get('balance', 0)
    user_portfolio_data['wallets'][currency]['balance'] += amount
    new_balance = user_portfolio_data['wallets'][currency]['balance']

    write_json_file(PORTFOLIOS_FILE, portfolios)
    
    return (f"Покупка выполнена: {amount:.4f} {currency}\n"
            f"Изменения в портфеле:\n"
            f"- {currency}: было {old_balance:.4f} → стало {new_balance:.4f}")


def sell(currency: str, amount: float) -> str:
    """Продажа валюты."""
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом.")

    current_user = get_current_user()
    if not current_user:
        raise PermissionError("Сначала выполните login.")

    portfolios = read_json_file(PORTFOLIOS_FILE)
    user_portfolio_data = next((p for p in portfolios if p['user_id'] == current_user.user_id), None)

    if not user_portfolio_data or currency not in user_portfolio_data.get('wallets', {}):
        raise ValueError(f"У вас нет кошелька '{currency}'.")

    wallet_data = user_portfolio_data['wallets'][currency]
    if wallet_data['balance'] < amount:
        raise InsufficientFundsError(code=currency, available=wallet_data['balance'], required=amount)
    
    old_balance = wallet_data['balance']
    wallet_data['balance'] -= amount
    new_balance = wallet_data['balance']
    
    write_json_file(PORTFOLIOS_FILE, portfolios)
    
    return (f"Продажа выполнена: {amount:.4f} {currency}\n"
            f"Изменения в портфеле:\n"
            f"- {currency}: было {old_balance:.4f} → стало {new_balance:.4f}")


def get_rate(from_currency: str, to_currency: str) -> str:
    """Получение курса валюты."""
    rates_data = read_json_file(RATES_FILE)
    pair = f"{from_currency}_{to_currency}"
    reverse_pair = f"{to_currency}_{from_currency}"

    rate = None
    updated_at = "N/A"
    
    if pair in rates_data:
        rate = rates_data[pair]['rate']
        updated_at = rates_data[pair]['updated_at']
    elif reverse_pair in rates_data:
        rate = 1 / rates_data[reverse_pair]['rate']
        updated_at = rates_data[reverse_pair]['updated_at']
    else:
        raise RateNotFoundError(code=f"{from_currency}→{to_currency}")

    reverse_rate = 1 / rate
    
    return (f"Курс {from_currency}→{to_currency}: {rate:.8f} (обновлено: {updated_at})\n"
            f"Обратный курс {to_currency}→{from_currency}: {reverse_rate:.8f}")

def update_rates(source=None):
    return "Обновление курсов пока не реализовано."

def show_rates(currency=None, top=None):
    return "Просмотр курсов пока не реализован."
