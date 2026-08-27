"""
Шаблоны для управления списком прокси в Telegram боте.
"""

import textwrap
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from settings import Settings as sett
from core.proxy_utils import format_proxy_display

from .. import callback_datas as calls


def settings_proxy_list_text(page: int = 0, per_page: int = 5):
    """Генерирует текст со списком прокси."""
    config = sett.get("config")
    proxy_list = sett.get("proxy_list") or {}
    current_proxy = config["playerok"]["api"]["proxy"]
    
    total = len(proxy_list)
    start = page * per_page
    end = start + per_page
    
    proxy_items = list(proxy_list.items())[start:end]
    
    text = "🌐 <b>Список прокси</b>\n\n"
    
    if not proxy_list:
        text += "📭 <i>Список прокси пуст</i>\n\n"
        text += "Добавьте прокси, нажав кнопку ниже.\n\n"
        text += "<i>💡 Рекомендуется HTTP/HTTPS прокси.\nSOCKS5 может работать менее стабильно.</i>"
    else:
        text += f"📊 Всего прокси: <b>{total}</b>\n"
        text += f"🔹 Активный: <code>{format_proxy_display(current_proxy) if current_proxy else '❌ Не выбран'}</code>\n\n"
        
        for proxy_id, proxy_str in proxy_items:
            is_active = "🟢" if proxy_str == current_proxy else "⚪"
            display = format_proxy_display(proxy_str)
            # Помечаем SOCKS прокси
            socks_mark = " ⚠️" if proxy_str.startswith(('socks5://', 'socks4://')) else ""
            text += f"{is_active} <code>{display}</code>{socks_mark} (ID: {proxy_id})\n"
    
    return text


def settings_proxy_list_kb(page: int = 0, per_page: int = 5):
    """Генерирует клавиатуру со списком прокси."""
    proxy_list = sett.get("proxy_list") or {}
    
    total = len(proxy_list)
    start = page * per_page
    end = start + per_page
    
    proxy_items = list(proxy_list.items())[start:end]
    
    rows = []
    
    # Кнопки прокси
    for proxy_id, proxy_str in proxy_items:
        display = format_proxy_display(proxy_str, max_length=25)
        rows.append([InlineKeyboardButton(
            text=f"📡 {display}",
            callback_data=calls.ProxyPage(proxy_id=int(proxy_id)).pack()
        )])
    
    # Пагинация
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=calls.ProxyListPagination(page=page-1).pack()
        ))
    if end < total:
        pagination_row.append(InlineKeyboardButton(
            text="Вперёд ▶️",
            callback_data=calls.ProxyListPagination(page=page+1).pack()
        ))
    
    if pagination_row:
        rows.append(pagination_row)
    
    # Кнопка добавления
    rows.append([InlineKeyboardButton(
        text="➕ Добавить прокси",
        callback_data="enter_new_proxy"
    )])
    
    # Кнопка назад
    rows.append([InlineKeyboardButton(
        text="⬅️ К настройкам аккаунта",
        callback_data=calls.SettingsNavigation(to="account").pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_proxy_page_text(proxy_id: int):
    """Генерирует текст страницы конкретного прокси."""
    config = sett.get("config")
    proxy_list = sett.get("proxy_list") or {}
    current_proxy = config["playerok"]["api"]["proxy"]
    
    proxy_str = proxy_list.get(str(proxy_id), "")
    
    if not proxy_str:
        return "❌ <b>Прокси не найден</b>"
    
    is_active = "🟢 Активен" if proxy_str == current_proxy else "⚪ Не активен"
    display = format_proxy_display(proxy_str)
    is_socks = proxy_str.startswith(('socks5://', 'socks4://'))
    
    text = textwrap.dedent(f"""
        📡 <b>Прокси #{proxy_id}</b>
        
        <b>Адрес:</b> <code>{display}</code>
        <b>Статус:</b> {is_active}
        <b>Тип:</b> {'SOCKS5 ⚠️' if is_socks else 'HTTP/HTTPS ✓'}
    """)
    
    if is_socks:
        text += "\n<i>⚠️ SOCKS прокси могут работать менее стабильно с Playerok. Рекомендуется HTTP/HTTPS.</i>\n"
    
    text += "\nВыберите действие ↓"
    
    return text


def settings_proxy_page_kb(proxy_id: int):
    """Генерирует клавиатуру для страницы прокси."""
    config = sett.get("config")
    proxy_list = sett.get("proxy_list") or {}
    current_proxy = config["playerok"]["api"]["proxy"]
    
    proxy_str = proxy_list.get(str(proxy_id), "")
    is_active = proxy_str == current_proxy
    
    rows = []
    
    # Кнопка активации/деактивации
    if not is_active:
        rows.append([InlineKeyboardButton(
            text="✅ Активировать этот прокси",
            callback_data=f"activate_proxy:{proxy_id}"
        )])
    else:
        rows.append([InlineKeyboardButton(
            text="🔴 Деактивировать прокси",
            callback_data=f"deactivate_proxy:{proxy_id}"
        )])
    
    # Кнопка проверки
    rows.append([InlineKeyboardButton(
        text="🔍 Проверить работоспособность",
        callback_data=f"check_proxy:{proxy_id}"
    )])
    
    # Кнопка удаления (только если не активен)
    if not is_active:
        rows.append([InlineKeyboardButton(
            text="❌ Удалить прокси",
            callback_data=f"delete_proxy:{proxy_id}"
        )])
    
    # Кнопка назад
    rows.append([InlineKeyboardButton(
        text="⬅️ К списку прокси",
        callback_data=calls.ProxyListPagination(page=0).pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_proxy_float_text(placeholder: str):
    """Генерирует текст для плавающих сообщений."""
    txt = textwrap.dedent(f"""
        🌐 <b>Управление прокси</b>
        \n{placeholder}
    """)
    return txt
