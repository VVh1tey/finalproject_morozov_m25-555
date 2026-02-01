import shlex
from functools import wraps
from typing import Dict, List, Optional, Any

import prompt
from prettytable import PrettyTable

from valutatrade_hub.core.currencies import get_all_currencies_info
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    RateNotFoundError,
)
from valutatrade_hub.core import usecases as usecase
from valutatrade_hub.infra.settings import settings


def print_help():
    """Выводит справочную информацию по командам."""
    table = PrettyTable()
    table.field_names = ["Команда", "Описание", "Пример"]
    table.align["Команда"] = "l"
    table.align["Описание"] = "l"
    table.align["Пример"] = "l"

    commands = [
        (
            "register --username <имя> --password <пароль>",
            "Регистрация нового пользователя",
            "register --username xx --password 1234",
        ),
        (
            "login --username <имя> --password <пароль>",
            "Вход в систему",
            "login --username xx --password 1234",
        ),
        (
            "show-portfolio [--base USD]",
            "Показать текущий портфель",
            "show-portfolio --base EUR",
        ),
        (
            "buy --currency <код> --amount <число>",
            "Купить валюту",
            "buy --currency BTC --amount 0.1",
        ),
        (
            "sell --currency <код> --amount <число>",
            "Продать валюту",
            "sell --currency BTC --amount 0.1",
        ),
        (
            "get-rate --from <код> --to <код>",
            "Получить курс валюты",
            "get-rate --from USD --to EUR",
        ),
        ("update-rates", "↻ Обновить кэш курсов валют", "update-rates"),
        ("show-rates", "📊 Показать актуальные курсы из кэша", "show-rates --top 5"),
        ("currencies", "Показать список доступных валют", "currencies"),
        ("help", "Показать это меню", "help"),
        ("exit", "Выйти из программы", "exit"),
    ]

    for cmd, desc, example in commands:
        table.add_row([cmd, desc, example])

    print("\n" + "=" * 90)
    print("Valutatrade Hub - Командный Интерфейс")
    print("=" * 90)
    print(table)
    print("=" * 90)
    print("Подсказка: Для выхода из программы введите 'exit'.")
    print("=" * 90)


def print_welcome():
    """Выводит приветственное сообщение."""
    print("\n============================================================")
    print("       Добро пожаловать в Valutatrade Hub!")
    print("============================================================\n")


def print_goodbye():
    """Выводит прощальное сообщение."""
    print("\n============================================================")
    print("    Спасибо за использование Valutatrade Hub! До свидания.")
    print("============================================================\n")


def get_arg(params: List[str], name: str, default=None) -> Optional[str]:
    """Извлекает значение аргумента из списка параметров."""
    try:
        index = params.index(name)
        if index + 1 < len(params) and not params[index + 1].startswith("--"):
            return params[index + 1]
    except ValueError:
        return default
    return default


def cli_command(
    required_args: Optional[List[str]] = None,
    optional_args: Optional[Dict[str, Any]] = None,
):
    """Декоратор для обработки CLI-команд."""
    required_args = required_args or []
    optional_args = optional_args or {}

    def decorator(fn):
        @wraps(fn)
        def wrapper(params: List[str]):
            try:
                parsed_args = {}
                for arg in required_args:
                    value = get_arg(params, arg)
                    if value is None:
                        raise ValueError(f"Отсутствует обязательный параметр: {arg}")
                    parsed_args[arg.lstrip("-")] = value

                for arg, default in optional_args.items():
                    value = get_arg(params, arg, default)
                    if value is not None:
                        parsed_args[arg.lstrip("-")] = value

                result = fn(**parsed_args)
                if result:
                    print(result)
            except (ValueError, PermissionError) as e:
                print(f"! Ошибка: {e}")
            except InsufficientFundsError as e:
                print(f"{e}")
            except (CurrencyNotFoundError, RateNotFoundError, ApiRequestError) as e:
                print(f"!! Ошибка: {e}")
            except Exception as e:
                print(f"!! Неожиданная системная ошибка: {type(e).__name__} - {e}")

        return wrapper

    return decorator


def cli():
    """Основная функция CLI с интерактивной оболочкой."""
    print_welcome()
    print_help()

    while True:
        try:
            user_input = prompt.string("> ").strip()
            if not user_input:
                continue

            args = shlex.split(user_input, posix=False)
            cmd, *params = args
            cmd = cmd.lower()

            if cmd == "exit":
                print_goodbye()
                break
            elif cmd == "help":
                print_help()
            elif cmd == "currencies":
                print("\n[i] Доступные валюты:")
                print(get_all_currencies_info())
            elif cmd == "register":

                @cli_command(required_args=["--username", "--password"])
                def cmd_register(username, password):
                    return f"✓ {usecase.register(username, password)}"

                cmd_register(params)
            elif cmd == "login":

                @cli_command(required_args=["--username", "--password"])
                def cmd_login(username, password):
                    return f"✓ {usecase.login(username, password)}"

                cmd_login(params)
            elif cmd == "show-portfolio":

                @cli_command(
                    optional_args={"--base": settings.get("DEFAULT_BASE_CURRENCY")}
                )
                def cmd_show(base):
                    return usecase.show_portfolio(base)

                cmd_show(params)
            elif cmd == "buy":

                @cli_command(required_args=["--currency", "--amount"])
                def cmd_buy(currency, amount):
                    return usecase.buy(currency, float(amount))

                cmd_buy(params)
            elif cmd == "sell":

                @cli_command(required_args=["--currency", "--amount"])
                def cmd_sell(currency, amount):
                    return usecase.sell(currency, float(amount))

                cmd_sell(params)
            elif cmd == "get-rate":

                @cli_command(required_args=["--from", "--to"])
                def cmd_get_rate(**kwargs):
                    return usecase.get_rate(kwargs["from"], kwargs["to"])

                cmd_get_rate(params)
            elif cmd == "update-rates":

                @cli_command()
                def cmd_update_rates():
                    return usecase.update_rates()

                cmd_update_rates(params)
            elif cmd == "show-rates":

                @cli_command(optional_args={"--currency": None, "--top": None})
                def cmd_show_rates(currency=None, top=None):
                    top_value = int(top) if top is not None else None
                    return usecase.show_rates(currency, top_value)

                cmd_show_rates(params)
            else:
                print(
                    f"[-] Неизвестная команда: '{cmd}'. Введите 'help' для списка команд."
                )
        except (KeyboardInterrupt, EOFError):
            print_goodbye()
            break
        except Exception as e:
            print(f"\n[!] Критическая ошибка в цикле CLI: {type(e).__name__} - {e}")
