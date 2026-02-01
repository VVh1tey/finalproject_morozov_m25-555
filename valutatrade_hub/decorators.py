import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

def log_action(action_name: str, verbose: bool = False) -> Callable:
    """
    Декоратор для логирования ключевых бизнес-операций.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            #NOTE: Импортируем внутри, чтобы избежать цикличного импорта, от этого ломается программа
            from valutatrade_hub.core.usecases import get_current_user
            
            user = get_current_user()
            username = user.username if user else "anonymous"

            # Улучшаем логирование для регистрации
            if action_name == "REGISTER" and 'username' in kwargs:
                log_username = kwargs['username']
            else:
                log_username = username
            
            log_context = {
                "action": action_name,
                "user": log_username,
                "func_args": args,
                "kwargs": kwargs,
            }

            logger.info(f"Attempting {action_name} for user '{log_username}' with kwargs={kwargs}")
            
            try:
                result = func(*args, **kwargs)
                # Для успешной регистрации обновляем имя пользователя в логе, если оно было anonymous
                if action_name == "REGISTER":
                    log_username = kwargs.get('username', log_username)

                log_context['result'] = 'OK'
                log_context['user'] = log_username
                if verbose:
                    log_context['return_value'] = result
                
                logger.info(f"Successfully completed {action_name} for user '{log_username}'.")
                return result
            except Exception as e:
                log_context['result'] = 'ERROR'
                log_context['error_type'] = type(e).__name__
                log_context['error_message'] = str(e)
                logger.error(
                    f"Failed {action_name} for user '{log_username}'. Error: {type(e).__name__} - {e}",
                    extra=log_context
                )
                raise # Пробрасываем исключение дальше
        return wrapper
    return decorator
