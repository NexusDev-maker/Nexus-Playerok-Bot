from __future__ import annotations

from logging import getLogger

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from settings import Settings as sett

from .. import templates as templ
from .. import callback_datas as calls
from .. import states
from ..helpful import throw_float_message

logger = getLogger("tgbot.data_replacement")
router = Router()


def _get_replacements() -> list[dict]:
    data = sett.get("data_replacements")
    return list(data) if isinstance(data, list) else []


def _save_replacements(replacements: list[dict]):
    sett.set("data_replacements", replacements)


def _parse_lines(text: str) -> list[str]:
    """Разбивает ввод на строки (по переносам строки или запятым)."""
    raw = text.replace("\r", "")
    parts: list[str] = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts.append(line)
    if len(parts) == 1 and "," in parts[0]:
        parts = [p.strip() for p in parts[0].split(",") if p.strip()]
    return parts


# НАВИГАЦИЯ

@router.callback_query(calls.DataReplacementsNavigation.filter())
async def callback_dr_navigation(callback: CallbackQuery, callback_data: calls.DataReplacementsNavigation, state: FSMContext):
    try:
        await state.set_state(None)
        await throw_float_message(
            state=state,
            message=callback.message,
            text=templ.data_replacements_text(),
            reply_markup=templ.data_replacements_kb(page=0),
            callback=callback,
        )
    except Exception as e:
        logger.error(f"Ошибка раздела замены данных: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(calls.DataReplacementsPagination.filter())
async def callback_dr_pagination(callback: CallbackQuery, callback_data: calls.DataReplacementsPagination, state: FSMContext):
    try:
        await state.set_state(None)
        await throw_float_message(
            state=state,
            message=callback.message,
            text=templ.data_replacements_text(),
            reply_markup=templ.data_replacements_kb(page=callback_data.page),
            callback=callback,
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(calls.DataReplacementPage.filter())
async def callback_dr_page(callback: CallbackQuery, callback_data: calls.DataReplacementPage, state: FSMContext):
    try:
        await state.set_state(None)
        await throw_float_message(
            state=state,
            message=callback.message,
            text=templ.data_replacement_page_text(callback_data.index),
            reply_markup=templ.data_replacement_page_kb(callback_data.index),
            callback=callback,
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(calls.DataReplacementAction.filter())
async def callback_dr_action(callback: CallbackQuery, callback_data: calls.DataReplacementAction, state: FSMContext):
    try:
        await state.set_state(None)
        action = callback_data.action
        index = callback_data.index
        replacements = _get_replacements()

        if index < 0 or index >= len(replacements):
            await callback.answer("❌ Правило не найдено.", show_alert=True)
            return

        if action == "toggle":
            replacements[index]["enabled"] = not replacements[index].get("enabled", True)
            _save_replacements(replacements)
            await throw_float_message(
                state=state,
                message=callback.message,
                text=templ.data_replacement_page_text(index),
                reply_markup=templ.data_replacement_page_kb(index),
                callback=callback,
            )
            return

        if action == "delete":
            await throw_float_message(
                state=state,
                message=callback.message,
                text=templ.data_replacements_float_text(f"🗑 Удалить правило #{index + 1}?"),
                reply_markup=templ.data_replacement_delete_confirm_kb(index),
                callback=callback,
            )
            return

        if action == "del_confirm":
            replacements.pop(index)
            _save_replacements(replacements)
            await callback.answer("✅ Правило удалено.")
            await throw_float_message(
                state=state,
                message=callback.message,
                text=templ.data_replacements_text(),
                reply_markup=templ.data_replacements_kb(page=0),
                callback=callback,
            )
            return

        await callback.answer("❌ Неизвестное действие.", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка действия замены данных ({callback_data.action}): {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


# ДОБАВЛЕНИЕ ПРАВИЛА

@router.callback_query(F.data == "enter_new_data_replacement")
async def callback_enter_new_dr(callback: CallbackQuery, state: FSMContext):
    await state.set_state(states.DataReplacementStates.waiting_for_new_keyphrases)
    await throw_float_message(
        state=state,
        message=callback.message,
        text=templ.data_replacements_float_text(
            "✍️ Введите <b>фразы для замены</b> (каждая с новой строки или через запятую) ↓\n"
            "Например: <code>{gift}</code>"
        ),
        reply_markup=templ.back_kb(calls.DataReplacementsNavigation(to="main").pack()),
        callback=callback,
    )


@router.message(states.DataReplacementStates.waiting_for_new_keyphrases, F.text)
async def handler_new_dr_keyphrases(message: Message, state: FSMContext):
    try:
        keyphrases = _parse_lines(message.text)
        if not keyphrases:
            raise Exception("❌ Нужно ввести хотя бы одну фразу")

        await state.update_data(dr_new_keyphrases=keyphrases)
        await state.set_state(states.DataReplacementStates.waiting_for_new_data)
        await throw_float_message(
            state=state,
            message=message,
            text=templ.data_replacements_float_text(
                "✍️ Теперь введите <b>значения</b>, на которые заменять (каждое с новой строки) ↓\n"
                "Если значений несколько — при замене выбирается случайное."
            ),
            reply_markup=templ.back_kb(calls.DataReplacementsNavigation(to="main").pack()),
        )
    except Exception as e:
        await throw_float_message(
            state=state,
            message=message,
            text=templ.data_replacements_float_text(str(e)),
            reply_markup=templ.back_kb(calls.DataReplacementsNavigation(to="main").pack()),
        )


@router.message(states.DataReplacementStates.waiting_for_new_data, F.text)
async def handler_new_dr_data(message: Message, state: FSMContext):
    try:
        data = _parse_lines(message.text)
        if not data:
            raise Exception("❌ Нужно ввести хотя бы одно значение")

        state_data = await state.get_data()
        keyphrases = state_data.get("dr_new_keyphrases") or []
        if not keyphrases:
            raise Exception("❌ Фразы потерялись, начните заново")

        replacements = _get_replacements()
        replacements.append({"enabled": True, "keyphrases": keyphrases, "data": data})
        _save_replacements(replacements)

        await state.set_state(None)
        await throw_float_message(
            state=state,
            message=message,
            text=templ.data_replacements_float_text(f"✅ Правило добавлено ({len(keyphrases)} фраз, {len(data)} значений)."),
            reply_markup=templ.data_replacements_kb(page=0),
        )
    except Exception as e:
        await throw_float_message(
            state=state,
            message=message,
            text=templ.data_replacements_float_text(str(e)),
            reply_markup=templ.back_kb(calls.DataReplacementsNavigation(to="main").pack()),
        )
