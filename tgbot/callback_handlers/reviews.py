from __future__ import annotations

import asyncio
from logging import getLogger

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from .. import templates as templ
from .. import callback_datas as calls
from ..helpful import get_playerok_bot, throw_float_message

logger = getLogger("tgbot.reviews")
router = Router()

PAGE_SIZE = 5


def _get_account():
    playerok_bot = get_playerok_bot()
    if playerok_bot is None:
        return None
    return getattr(playerok_bot, "account", None) or getattr(playerok_bot, "playerok_account", None)


async def _run(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def _show_reviews(callback: CallbackQuery, state: FSMContext, page: int, after_cursor: str | None):
    account = _get_account()
    if account is None:
        await callback.answer("❌ Аккаунт Playerok недоступен.", show_alert=True)
        return

    try:
        review_list = await _run(account.get_reviews, count=PAGE_SIZE, after_cursor=after_cursor)
    except Exception as e:
        logger.error(f"Не удалось получить отзывы: {e}", exc_info=True)
        await callback.answer(f"❌ Не удалось загрузить отзывы: {e}", show_alert=True)
        return

    page_info = getattr(review_list, "page_info", None)
    has_next = bool(getattr(page_info, "has_next_page", False))
    has_prev = page > 0

    await throw_float_message(
        state=state,
        message=callback.message,
        text=templ.reviews_text(review_list, page),
        reply_markup=templ.reviews_kb(page=page, has_prev=has_prev, has_next=has_next),
        callback=callback,
    )


@router.callback_query(calls.ReviewsNavigation.filter())
async def callback_reviews_navigation(callback: CallbackQuery, callback_data: calls.ReviewsNavigation, state: FSMContext):
    try:
        await state.set_state(None)
        await state.update_data(rev_cursors=[None], rev_page=0)
        await _show_reviews(callback, state, page=0, after_cursor=None)
    except Exception as e:
        logger.error(f"Ошибка в разделе отзывов: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(calls.ReviewsAction.filter())
async def callback_reviews_action(callback: CallbackQuery, callback_data: calls.ReviewsAction, state: FSMContext):
    try:
        await state.set_state(None)
        action = callback_data.action

        data = await state.get_data()
        cursors = list(data.get("rev_cursors") or [None])
        page = int(data.get("rev_page") or 0)

        account = _get_account()
        if account is None:
            await callback.answer("❌ Аккаунт Playerok недоступен.", show_alert=True)
            return

        if action == "refresh":
            after = cursors[page] if page < len(cursors) else None
            await _show_reviews(callback, state, page=page, after_cursor=after)
            return

        if action == "prev":
            if page <= 0:
                await callback.answer("Это первая страница.")
                return
            page -= 1
            await state.update_data(rev_page=page)
            await _show_reviews(callback, state, page=page, after_cursor=cursors[page])
            return

        if action == "next":
            after_current = cursors[page] if page < len(cursors) else None
            review_list = await _run(account.get_reviews, count=PAGE_SIZE, after_cursor=after_current)
            page_info = getattr(review_list, "page_info", None)
            if not getattr(page_info, "has_next_page", False):
                await callback.answer("Это последняя страница.")
                return
            end_cursor = getattr(page_info, "end_cursor", None)
            page += 1
            if page < len(cursors):
                cursors[page] = end_cursor
                cursors = cursors[: page + 1]
            else:
                cursors.append(end_cursor)
            await state.update_data(rev_cursors=cursors, rev_page=page)
            await _show_reviews(callback, state, page=page, after_cursor=end_cursor)
            return

        await callback.answer("❌ Неизвестное действие.", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка действия отзывов ({callback_data.action}): {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
