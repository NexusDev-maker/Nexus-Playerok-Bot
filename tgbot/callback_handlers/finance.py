from __future__ import annotations

import asyncio
from logging import getLogger

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from .. import templates as templ
from .. import callback_datas as calls
from ..helpful import get_playerok_bot, throw_float_message

logger = getLogger("tgbot.finance")
router = Router()

TX_PAGE_SIZE = 8
CARDS_PAGE_SIZE = 24


def _get_account():
    playerok_bot = get_playerok_bot()
    if playerok_bot is None:
        return None
    return getattr(playerok_bot, "account", None) or getattr(playerok_bot, "playerok_account", None)


async def _run(func, *args, **kwargs):
    """Выполняет блокирующий вызов API в отдельном потоке."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


# НАВИГАЦИЯ ФИНАНСОВ

@router.callback_query(calls.FinanceNavigation.filter())
async def callback_finance_navigation(callback: CallbackQuery, callback_data: calls.FinanceNavigation, state: FSMContext):
    try:
        await state.set_state(None)
        to = callback_data.to

        if to in ("default", "main"):
            await throw_float_message(
                state=state,
                message=callback.message,
                text=templ.finance_main_text(),
                reply_markup=templ.finance_main_kb(),
                callback=callback,
            )

        elif to == "transactions":
            # Сбрасываем стек курсоров и показываем первую страницу
            await state.update_data(fin_tx_cursors=[None], fin_tx_page=0)
            await _show_transactions(callback, state, page=0, after_cursor=None)

        elif to == "cards":
            await _show_cards(callback, state)

        elif to == "withdraw":
            from .withdrawal import start_withdrawal
            await start_withdrawal(callback, state)

        else:
            await callback.answer("❌ Неизвестный раздел.", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка в разделе финансов ({callback_data.to}): {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


# ТРАНЗАКЦИИ

async def _show_transactions(callback: CallbackQuery, state: FSMContext, page: int, after_cursor: str | None):
    account = _get_account()
    if account is None:
        await callback.answer("❌ Аккаунт Playerok недоступен.", show_alert=True)
        return

    try:
        tx_list = await _run(account.get_transactions, count=TX_PAGE_SIZE, after_cursor=after_cursor)
    except Exception as e:
        logger.error(f"Не удалось получить транзакции: {e}", exc_info=True)
        await callback.answer(f"❌ Не удалось загрузить транзакции: {e}", show_alert=True)
        return

    page_info = getattr(tx_list, "page_info", None)
    has_next = bool(getattr(page_info, "has_next_page", False))
    has_prev = page > 0

    await throw_float_message(
        state=state,
        message=callback.message,
        text=templ.transactions_text(tx_list, page),
        reply_markup=templ.transactions_kb(page=page, has_prev=has_prev, has_next=has_next),
        callback=callback,
    )


@router.callback_query(calls.FinanceAction.filter())
async def callback_finance_action(callback: CallbackQuery, callback_data: calls.FinanceAction, state: FSMContext):
    try:
        await state.set_state(None)
        action = callback_data.action

        data = await state.get_data()
        cursors = list(data.get("fin_tx_cursors") or [None])
        page = int(data.get("fin_tx_page") or 0)

        account = _get_account()
        if account is None:
            await callback.answer("❌ Аккаунт Playerok недоступен.", show_alert=True)
            return

        if action == "tx_refresh":
            after = cursors[page] if page < len(cursors) else None
            await _show_transactions(callback, state, page=page, after_cursor=after)
            return

        if action == "tx_prev":
            if page <= 0:
                await callback.answer("Это первая страница.")
                return
            page -= 1
            after = cursors[page]
            await state.update_data(fin_tx_page=page)
            await _show_transactions(callback, state, page=page, after_cursor=after)
            return

        if action == "tx_next":
            # Получаем end_cursor текущей страницы, чтобы загрузить следующую
            after_current = cursors[page] if page < len(cursors) else None
            tx_list = await _run(account.get_transactions, count=TX_PAGE_SIZE, after_cursor=after_current)
            page_info = getattr(tx_list, "page_info", None)
            if not getattr(page_info, "has_next_page", False):
                await callback.answer("Это последняя страница.")
                return
            end_cursor = getattr(page_info, "end_cursor", None)
            page += 1
            # запоминаем курсор для новой страницы
            if page < len(cursors):
                cursors[page] = end_cursor
                cursors = cursors[: page + 1]
            else:
                cursors.append(end_cursor)
            await state.update_data(fin_tx_cursors=cursors, fin_tx_page=page)
            await _show_transactions(callback, state, page=page, after_cursor=end_cursor)
            return

        await callback.answer("❌ Неизвестное действие.", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка действия финансов ({callback_data.action}): {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


# КАРТЫ

async def _show_cards(callback: CallbackQuery, state: FSMContext):
    account = _get_account()
    if account is None:
        await callback.answer("❌ Аккаунт Playerok недоступен.", show_alert=True)
        return

    try:
        card_list = await _run(account.get_verified_cards, count=CARDS_PAGE_SIZE)
    except Exception as e:
        logger.error(f"Не удалось получить карты: {e}", exc_info=True)
        await callback.answer(f"❌ Не удалось загрузить карты: {e}", show_alert=True)
        return

    await throw_float_message(
        state=state,
        message=callback.message,
        text=templ.cards_text(card_list),
        reply_markup=templ.cards_kb(card_list),
        callback=callback,
    )


@router.callback_query(calls.CardAction.filter())
async def callback_card_action(callback: CallbackQuery, callback_data: calls.CardAction, state: FSMContext):
    try:
        await state.set_state(None)
        action = callback_data.action
        card_id = callback_data.card_id

        account = _get_account()
        if account is None:
            await callback.answer("❌ Аккаунт Playerok недоступен.", show_alert=True)
            return

        if action == "del":
            # Ищем карту, чтобы показать подтверждение
            card_list = await _run(account.get_verified_cards, count=CARDS_PAGE_SIZE)
            card = next((c for c in getattr(card_list, "bank_cards", []) if c.id == card_id), None)
            if card is None:
                await callback.answer("❌ Карта не найдена.", show_alert=True)
                return
            await throw_float_message(
                state=state,
                message=callback.message,
                text=templ.card_delete_confirm_text(card),
                reply_markup=templ.card_delete_confirm_kb(card_id),
                callback=callback,
            )
            return

        if action == "del_confirm":
            await _run(account.delete_card, card_id)
            await callback.answer("✅ Карта удалена.")
            await _show_cards(callback, state)
            return

        await callback.answer("❌ Неизвестное действие.", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка действия с картой ({callback_data.action}): {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
