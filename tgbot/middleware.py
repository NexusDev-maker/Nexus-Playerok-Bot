from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
import logging
import traceback

from settings import Settings as sett
from .helpful import do_auth
from . import states


logger = logging.getLogger("seal.middleware")


class BrandLockMiddleware(BaseMiddleware):
    """Блокирует бота, если данные бренда изменены на чужие."""

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        try:
            from core.brand import is_brand_changed, TAMPER_MESSAGE
        except Exception:
            return await handler(event, data)

        if is_brand_changed():
            try:
                if isinstance(event, Message):
                    await event.answer(TAMPER_MESSAGE, parse_mode="HTML")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🦅 Айай, негодяй! Верни оригинал: @NexusPlayerok", show_alert=True)
            except Exception:
                pass
            return

        return await handler(event, data)


class PluginStateMiddleware(BaseMiddleware):
    """
    Middleware для проверки статуса плагинов.
    Блокирует выполнение обработчиков неактивных плагинов.
    """
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        from core.plugins import get_plugins
        
        # Получаем информацию о текущем обработчике
        handler_info = data.get("handler", None)
        if handler_info:
            # Пытаемся определить, принадлежит ли обработчик плагину
            handler_module = getattr(handler, "__module__", None)
            
            if handler_module and handler_module.startswith("plugins."):
                # Извлекаем имя плагина из модуля (например, "plugins.my_plugin.handlers" -> "my_plugin")
                plugin_dir_name = handler_module.split(".")[1] if len(handler_module.split(".")) > 1 else None
                
                if plugin_dir_name:
                    # Ищем плагин по имени директории
                    plugin = None
                    for p in get_plugins():
                        if p._dir_name == plugin_dir_name:
                            plugin = p
                            break
                    
                    # Если плагин найден и он неактивен, блокируем выполнение
                    if plugin and not plugin.enabled:
                        logger.debug(f"Заблокирован обработчик неактивного плагина: {plugin.meta.name}")
                        if isinstance(event, CallbackQuery):
                            try:
                                await event.answer(
                                    f"⚠️ Плагин '{plugin.meta.name}' отключен",
                                    show_alert=True
                                )
                            except:
                                pass
                        return  # Блокируем выполнение обработчика
        
        # Если проверка пройдена или обработчик не принадлежит плагину, продолжаем
        return await handler(event, data)


class AuthMiddleware(BaseMiddleware):
    """
    Middleware для проверки авторизации пользователя.
    Блокирует доступ к боту, если пользователь не авторизован.
    """
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        from aiogram.fsm.context import FSMContext
        
        config = sett.get("config")
        state: FSMContext = data.get("state")
        
        # Проверяем, авторизован ли пользователь
        user_id = event.from_user.id if event.from_user else None
        
        if not user_id:
            return await handler(event, data)
        
        # Проверяем, включена ли блокировка входа по паролю
        password_auth_enabled = config["telegram"]["bot"].get("password_auth_enabled", True)
        
        # Если пользователь не авторизован и блокировка включена
        if user_id not in config["telegram"]["bot"]["signed_users"] and password_auth_enabled:
            # Получаем текущее состояние
            current_state = await state.get_state() if state else None
            
            # Проверяем, находится ли пользователь в состоянии ожидания пароля
            waiting_for_password_state = states.SystemStates.waiting_for_password
            is_waiting_for_password = (
                current_state == waiting_for_password_state or
                (current_state and str(current_state) == str(waiting_for_password_state))
            )
            
            # Если это не состояние ожидания пароля, запрашиваем авторизацию
            if not is_waiting_for_password:
                if isinstance(event, Message):
                    # Если это команда /start, пропускаем (она обрабатывается отдельно)
                    if event.text and event.text.startswith("/start"):
                        return await handler(event, data)
                    # Для остальных сообщений запрашиваем авторизацию
                    return await do_auth(event, state)
                elif isinstance(event, CallbackQuery):
                    # Для callback-запросов также запрашиваем авторизацию
                    try:
                        await event.answer("🔐 Требуется авторизация. Используйте команду /start", show_alert=True)
                    except:
                        pass
                    return
        
        # Если пользователь авторизован, пропускаем запрос дальше
        return await handler(event, data)


class ErrorMiddleware(BaseMiddleware):
    """
    Middleware для перехвата и логирования всех ошибок в роутерах.
    Записывает подробную информацию об ошибке в лог-файл.
    """
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        try:
            # Пытаемся выполнить обработчик
            return await handler(event, data)
        except Exception as e:
            # Получаем информацию об ошибке
            error_traceback = traceback.format_exc()
            
            # Получаем информацию о пользователе
            user_id = event.from_user.id if event.from_user else "Unknown"
            username = event.from_user.username if event.from_user else "Unknown"
            
            # Получаем информацию о типе события
            if isinstance(event, Message):
                event_type = "Message"
                event_info = f"Text: {event.text[:100] if event.text else 'No text'}"
            elif isinstance(event, CallbackQuery):
                event_type = "CallbackQuery"
                event_info = f"Data: {event.data}"
            else:
                event_type = type(event).__name__
                event_info = "Unknown event"
            
            # Получаем имя обработчика
            handler_name = getattr(handler, "__name__", "Unknown handler")
            handler_module = getattr(handler, "__module__", "Unknown module")
            
            # Логируем ошибку с подробной информацией
            logger.error(
                f"\n{'='*80}\n"
                f"ERROR IN ROUTER HANDLER\n"
                f"{'='*80}\n"
                f"Handler: {handler_module}.{handler_name}\n"
                f"Event Type: {event_type}\n"
                f"Event Info: {event_info}\n"
                f"User ID: {user_id} (@{username})\n"
                f"Error: {type(e).__name__}: {str(e)}\n"
                f"{'-'*80}\n"
                f"Traceback:\n{error_traceback}"
                f"{'='*80}\n"
            )
            
            # Пытаемся отправить пользователю сообщение об ошибке
            try:
                error_message = (
                    "⚠️ <b>Произошла ошибка при обработке запроса</b>\n\n"
                    f"<code>{type(e).__name__}: {str(e)[:200]}</code>\n\n"
                    "Ошибка была записана в лог. Попробуйте повторить действие позже."
                )
                
                if isinstance(event, Message):
                    await event.answer(error_message, parse_mode="HTML")
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        f"⚠️ Ошибка: {type(e).__name__}",
                        show_alert=True
                    )
                    # Также отправляем подробное сообщение в чат
                    if event.message:
                        await event.message.answer(error_message, parse_mode="HTML")
            except Exception as notify_error:
                logger.error(f"Не удалось отправить уведомление об ошибке пользователю: {notify_error}")
            
            # Не пробрасываем исключение дальше, чтобы бот не упал
            return None

