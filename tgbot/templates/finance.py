import textwrap
from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .. import callback_datas as calls


# Человекочитаемые названия операций транзакций
_OPERATION_LABELS = {
    "DEPOSIT": "💵 Пополнение",
    "BUY": "🛍️ Покупка товара",
    "SELL": "🛒 Продажа товара",
    "ITEM_DEFAULT_PRIORITY": "📌 Бесплатный приоритет",
    "ITEM_PREMIUM_PRIORITY": "⭐ Премиум приоритет",
    "WITHDRAW": "💸 Вывод средств",
    "MANUAL_BALANCE_INCREASE": "➕ Начисление на баланс",
    "MANUAL_BALANCE_DECREASE": "➖ Списание с баланса",
    "REFERRAL_BONUS": "🤝 Реферальный бонус",
    "STEAM_DEPOSIT": "🎮 Пополнение Steam",
}

_STATUS_LABELS = {
    "PENDING": "⏳ В ожидании",
    "PROCESSING": "❄️ В заморозке",
    "CONFIRMED": "✅ Подтверждена",
    "ROLLED_BACK": "↩️ Возврат",
    "FAILED": "❌ Ошибка",
}

_CARD_TYPE_LABELS = {
    "MIR": "МИР",
    "VISA": "VISA",
    "MASTERCARD": "Mastercard",
}


def _enum_name(value) -> str:
    """Безопасно получает имя enum-значения (или строку)."""
    return getattr(value, "name", str(value)) if value is not None else ""


def _format_date(raw: str | None) -> str:
    if not raw:
        return "—"
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(raw)


def _not_connected_text() -> str:
    return textwrap.dedent("""
        ❌ <b>Не удалось подключиться к аккаунту</b>

        Playerok аккаунт недоступен. Проверьте настройки:
        ⚙️ <b>Настройки</b> → <b>🔑 Аккаунт</b>

        После изменения настроек используйте /restart
    """).strip()


# ГЛАВНЫЙ ЭКРАН ФИНАНСОВ

def finance_main_text() -> str:
    from plbot.playerokbot import get_playerok_bot

    plbot = get_playerok_bot()
    if not plbot or not getattr(plbot, "is_connected", False) or not getattr(plbot, "playerok_account", None):
        return _not_connected_text()

    try:
        acc = plbot.playerok_account.get()
        balance = acc.profile.balance
    except Exception as e:
        return f"❌ Не удалось получить баланс: <code>{e}</code>"

    return textwrap.dedent(f"""
        💰 <b>Финансы</b>

        <b>Баланс:</b> {balance.value}₽
          ┣ <b>👜 Доступно:</b> {balance.available}₽
          ┣ <b>⌛ В процессе:</b> {balance.pending_income}₽
          ┗ <b>❄️ Заморожено:</b> {balance.frozen}₽

        Выберите раздел ↓
    """).strip()


def finance_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 История транзакций", callback_data=calls.FinanceNavigation(to="transactions").pack())],
        [InlineKeyboardButton(text="💳 Мои карты", callback_data=calls.FinanceNavigation(to="cards").pack())],
        [InlineKeyboardButton(text="💸 Вывести средства", callback_data=calls.FinanceNavigation(to="withdraw").pack())],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=calls.FinanceNavigation(to="main").pack())],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=calls.MenuPagination(page=1).pack())],
    ])


# ТРАНЗАКЦИИ

def transactions_text(tx_list, page: int) -> str:
    transactions = getattr(tx_list, "transactions", []) or []
    if not transactions:
        return textwrap.dedent("""
            📜 <b>История транзакций</b>

            Пока нет ни одной транзакции.
        """).strip()

    lines = ["📜 <b>История транзакций</b>", f"<i>Страница {page + 1}</i>", ""]
    for tx in transactions:
        op = _OPERATION_LABELS.get(_enum_name(tx.operation), _enum_name(tx.operation) or "Операция")
        status = _STATUS_LABELS.get(_enum_name(tx.status), _enum_name(tx.status))
        sign = "−" if _enum_name(tx.direction) == "OUT" else "+"
        value = getattr(tx, "value", 0)
        fee = getattr(tx, "fee", 0) or 0
        date = _format_date(getattr(tx, "created_at", None))

        line = f"{op}\n  ┣ <b>{sign}{value}₽</b>"
        if fee:
            line += f" (комиссия {fee}₽)"
        line += f"\n  ┣ {status}"
        if getattr(tx, "sbp_bank_name", None):
            line += f"\n  ┣ 🏦 {tx.sbp_bank_name}"
        line += f"\n  ┗ 🕒 {date}"
        lines.append(line)
        lines.append("")

    return "\n".join(lines).strip()


def transactions_kb(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    nav_row = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=calls.FinanceAction(action="tx_prev").pack()))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}", callback_data="page_info"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="➡️ Далее", callback_data=calls.FinanceAction(action="tx_next").pack()))

    return InlineKeyboardMarkup(inline_keyboard=[
        nav_row,
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=calls.FinanceAction(action="tx_refresh").pack())],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=calls.FinanceNavigation(to="main").pack())],
    ])


# КАРТЫ

def cards_text(card_list) -> str:
    cards = getattr(card_list, "bank_cards", []) or []
    if not cards:
        return textwrap.dedent("""
            💳 <b>Мои карты</b>

            У вас пока нет привязанных банковских карт.
            Карту можно привязать на сайте Playerok при первом выводе.
        """).strip()

    lines = ["💳 <b>Мои карты</b>", ""]
    for card in cards:
        card_type = _CARD_TYPE_LABELS.get(_enum_name(card.card_type), _enum_name(card.card_type) or "Карта")
        chosen = " ⭐" if getattr(card, "is_chosen", False) else ""
        lines.append(f"• <b>{card_type}</b>{chosen}\n  ┗ <code>{card.card_first_six}••••{card.card_last_four}</code>")
        lines.append("")
    lines.append("Нажмите на карту ниже, чтобы удалить её.")
    return "\n".join(lines).strip()


def cards_kb(card_list) -> InlineKeyboardMarkup:
    rows = []
    cards = getattr(card_list, "bank_cards", []) or []
    for card in cards:
        card_type = _CARD_TYPE_LABELS.get(_enum_name(card.card_type), "Карта")
        rows.append([InlineKeyboardButton(
            text=f"🗑 {card_type} ••{card.card_last_four}",
            callback_data=calls.CardAction(action="del", card_id=card.id).pack(),
        )])
    rows.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=calls.FinanceNavigation(to="cards").pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=calls.FinanceNavigation(to="main").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def card_delete_confirm_text(card) -> str:
    card_type = _CARD_TYPE_LABELS.get(_enum_name(card.card_type), "Карта")
    return (
        f"🗑 <b>Удалить карту?</b>\n\n"
        f"<b>{card_type}</b> <code>{card.card_first_six}••••{card.card_last_four}</code>\n\n"
        f"Это действие необратимо (карту можно будет привязать заново)."
    )


def card_delete_confirm_kb(card_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=calls.CardAction(action="del_confirm", card_id=card_id).pack())],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data=calls.FinanceNavigation(to="cards").pack())],
    ])


# ВЫВОД СРЕДСТВ

# Провайдеры вывода: value = имя TransactionProviderIds
WITHDRAW_METHODS = [
    ("SBP", "🏦 СБП (по номеру телефона)"),
    ("BANK_CARD_RU", "💳 Карта РФ"),
    ("BANK_CARD_BY", "💳 Карта Беларуси"),
    ("BANK_CARD", "💳 Иностранная карта"),
    ("USDT", "🪙 USDT (TRC20)"),
]

_METHOD_LABELS = {name: label for name, label in WITHDRAW_METHODS}


def withdraw_method_text(available: int | str) -> str:
    return textwrap.dedent(f"""
        💸 <b>Вывод средств</b>

        <b>👜 Доступно к выводу:</b> {available}₽

        Выберите способ вывода ↓

        ⚠️ Все переводы делаете вы сами и подтверждаете вручную.
    """).strip()


def withdraw_method_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data=calls.WithdrawAction(action="provider", value=name).pack())]
            for name, label in WITHDRAW_METHODS]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=calls.FinanceNavigation(to="main").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def withdraw_cards_text(card_list) -> str:
    cards = getattr(card_list, "bank_cards", []) or []
    if not cards:
        return (
            "💳 <b>Вывод на карту</b>\n\n"
            "У вас нет привязанных карт. Привяжите карту на сайте Playerok "
            "(при первом выводе), затем повторите."
        )
    return "💳 <b>Вывод на карту</b>\n\nВыберите карту для вывода ↓"


def withdraw_cards_kb(card_list) -> InlineKeyboardMarkup:
    rows = []
    for card in getattr(card_list, "bank_cards", []) or []:
        card_type = _CARD_TYPE_LABELS.get(_enum_name(card.card_type), "Карта")
        rows.append([InlineKeyboardButton(
            text=f"💳 {card_type} ••{card.card_last_four}",
            callback_data=calls.WithdrawAction(action="card", value=card.id).pack(),
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=calls.FinanceNavigation(to="withdraw").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def withdraw_sbp_banks_text() -> str:
    return "🏦 <b>Вывод через СБП</b>\n\nВыберите банк получателя ↓"


def withdraw_sbp_banks_kb(members) -> InlineKeyboardMarkup:
    rows = []
    for m in members or []:
        rows.append([InlineKeyboardButton(
            text=f"🏦 {m.name}",
            callback_data=calls.WithdrawAction(action="sbp_bank", value=m.id).pack(),
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=calls.FinanceNavigation(to="withdraw").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def withdraw_float_text(placeholder) -> str:
    return f"💸 <b>Вывод средств</b>\n\n{placeholder}"


def withdraw_confirm_text(method_name: str, account_display: str, amount: int, extra: str | None = None) -> str:
    method_label = _METHOD_LABELS.get(method_name, method_name)
    txt = (
        f"💸 <b>Подтверждение вывода</b>\n\n"
        f"<b>Способ:</b> {method_label}\n"
        f"<b>Получатель:</b> <code>{account_display}</code>\n"
    )
    if extra:
        txt += f"<b>Банк:</b> {extra}\n"
    txt += (
        f"<b>Сумма:</b> {amount}₽\n\n"
        f"⚠️ Проверьте данные. Деньги будут отправлены сразу после подтверждения."
    )
    return txt


def withdraw_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить вывод", callback_data=calls.WithdrawAction(action="confirm").pack())],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=calls.WithdrawAction(action="cancel").pack())],
    ])
