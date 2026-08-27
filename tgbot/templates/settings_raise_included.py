import textwrap
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from settings import Settings as sett

from .. import callback_datas as calls


def settings_raise_included_text():
    included_raise_items = sett.get("auto_raise_items").get("included")
    txt = textwrap.dedent(f"""
        <b>📈 Автоподнятие → ➕ Включенные</b>

        Здесь вы можете добавить товары, которые будут автоматически подниматься.
        Товары добавляются по ключевым фразам в названии.

        <b>Всего включено:</b> {len(included_raise_items)}
    """)
    return txt


def settings_raise_included_kb(page: int = 0):
    included_raise_items: list[list] = sett.get("auto_raise_items").get("included")
    rows = []
    items_per_page = 7
    start = page * items_per_page
    end = start + items_per_page
    
    for i, keyphrases in enumerate(included_raise_items[start:end], start=start):
        keyphrases_str = ", ".join(keyphrases)
        rows.append([InlineKeyboardButton(
            text=f"🗑 {keyphrases_str[:30]}{'...' if len(keyphrases_str) > 30 else ''}",
            callback_data=calls.DeleteIncludedRaiseItem(index=i).pack()
        )])
    
    # Кнопки управления
    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data="add_included_raise_item")])
    rows.append([InlineKeyboardButton(text="📄 Добавить из файла", callback_data="add_included_raise_items_from_file")])
    
    # Пагинация
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=calls.IncludedRaiseItemsPagination(page=page-1).pack()))
    
    total_pages = (len(included_raise_items) + items_per_page - 1) // items_per_page
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="page_info"))
    
    if end < len(included_raise_items):
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=calls.IncludedRaiseItemsPagination(page=page+1).pack()))
    
    if nav_row:
        rows.append(nav_row)
    
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=calls.SettingsNavigation(to="raise").pack())])
    
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    return kb


def settings_new_raise_included_float_text(placeholder: str):
    txt = textwrap.dedent(f"""
        <b>📈 Автоподнятие → ➕ Включенные → ➕ Добавить</b>
        \n{placeholder}
    """)
    return txt
