import math
import textwrap

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from settings import Settings as sett

from .. import callback_datas as calls


ITEMS_PER_PAGE = 7


def _get_replacements() -> list[dict]:
    data = sett.get("data_replacements")
    return data if isinstance(data, list) else []


def data_replacements_text() -> str:
    replacements = _get_replacements()
    enabled = sum(1 for r in replacements if r.get("enabled", True))
    return textwrap.dedent(f"""
        🔁 <b>Замена данных</b>
        Всего правил: <b>{len(replacements)}</b> (включено: <b>{enabled}</b>)

        Правила автоматически заменяют указанные фразы в исходящих сообщениях бота.
        Нажмите на правило, чтобы открыть его ↓
    """).strip()


def data_replacements_kb(page: int = 0) -> InlineKeyboardMarkup:
    replacements = _get_replacements()
    rows = []

    total_pages = math.ceil(len(replacements) / ITEMS_PER_PAGE)
    total_pages = total_pages if total_pages > 0 else 1
    if page < 0:
        page = 0
    elif page >= total_pages:
        page = total_pages - 1

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE

    for index in range(start, min(end, len(replacements))):
        rule = replacements[index]
        status = "✅" if rule.get("enabled", True) else "❌"
        keyphrases = rule.get("keyphrases", [])
        label = keyphrases[0] if keyphrases else "—"
        if len(label) > 24:
            label = label[:24] + "…"
        rows.append([InlineKeyboardButton(
            text=f"{status} {label} ({len(rule.get('data', []))})",
            callback_data=calls.DataReplacementPage(index=index).pack(),
        )])

    if total_pages > 1:
        nav = []
        nav.append(InlineKeyboardButton(text="←", callback_data=calls.DataReplacementsPagination(page=page - 1).pack())
                   if page > 0 else InlineKeyboardButton(text="🛑", callback_data="page_info"))
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="page_info"))
        nav.append(InlineKeyboardButton(text="→", callback_data=calls.DataReplacementsPagination(page=page + 1).pack())
                   if page < total_pages - 1 else InlineKeyboardButton(text="🛑", callback_data="page_info"))
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="➕ Добавить правило", callback_data="enter_new_data_replacement")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=calls.MenuPagination(page=1).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def data_replacement_page_text(index: int) -> str:
    replacements = _get_replacements()
    if index < 0 or index >= len(replacements):
        return "❌ Правило не найдено."
    rule = replacements[index]
    status = "✅ Включено" if rule.get("enabled", True) else "❌ Выключено"
    keyphrases = "\n".join(f"• <code>{k}</code>" for k in rule.get("keyphrases", [])) or "—"
    data = "\n".join(f"• {d}" for d in rule.get("data", [])) or "—"
    return textwrap.dedent(f"""
        🔁 <b>Правило замены #{index + 1}</b>
        Статус: <b>{status}</b>

        <b>Заменять фразы:</b>
        {keyphrases}

        <b>На значения:</b>
        {data}
    """).strip()


def data_replacement_page_kb(index: int) -> InlineKeyboardMarkup:
    replacements = _get_replacements()
    enabled = replacements[index].get("enabled", True) if 0 <= index < len(replacements) else True
    toggle_text = "❌ Выключить" if enabled else "✅ Включить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=calls.DataReplacementAction(action="toggle", index=index).pack())],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=calls.DataReplacementAction(action="delete", index=index).pack())],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=calls.DataReplacementsNavigation(to="main").pack())],
    ])


def data_replacement_delete_confirm_kb(index: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=calls.DataReplacementAction(action="del_confirm", index=index).pack())],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data=calls.DataReplacementPage(index=index).pack())],
    ])


def data_replacements_float_text(placeholder) -> str:
    return f"🔁 <b>Замена данных</b>\n\n{placeholder}"
