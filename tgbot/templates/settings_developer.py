import textwrap
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from settings import Settings as sett

from .. import callback_datas as calls


def settings_developer_text():
    config = sett.get("config")
    requests_timeout = config["playerok"]["api"]["requests_timeout"] or "❌ Не задан"
    listener_requests_delay = config["playerok"]["api"]["listener_requests_delay"] or "❌ Не задан"
    
    txt = textwrap.dedent(f"""
        👨‍💻 <b>Настройки разработчика</b>

        <b>Параметры запросов:</b>
        ┣ 🛜 Таймаут: <b>{requests_timeout}</b> сек
        ┗ ⏱️ Периодичность: <b>{listener_requests_delay}</b> сек

        <i>💡 Таймаут</i> — максимальное время ожидания ответа от Playerok
        <i>💡 Периодичность</i> — интервал между запросами (рекомендуется ≥4 сек)

        Выберите параметр для изменения ↓
    """)
    return txt


def settings_developer_kb():
    rows = [
        [InlineKeyboardButton(text="🛜 Изменить таймаут", callback_data="enter_requests_timeout")],
        [InlineKeyboardButton(text="⏱️ Изменить периодичность", callback_data="enter_listener_requests_delay")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=calls.MenuPagination(page=1).pack())]
    ]
    
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    return kb


def settings_developer_float_text(placeholder: str):
    txt = textwrap.dedent(f"""
        👨‍💻 <b>Настройки разработчика</b>
        \n{placeholder}
    """)
    return txt
