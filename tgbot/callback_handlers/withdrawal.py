from __future__ import annotations

import asyncio
from logging import getLogger

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from playerokapi.enums import TransactionProviderIds

from .. import templates as templ
from .. import callback_datas as calls
from .. import states
from ..helpful import get_playerok_bot, throw_float_message

logger = getLogger("tgbot.withdrawal")
router = Router()

CARDS_PAGE_SIZE = 24


def _get_account():
    playerok_bot = get_playerok_bot()
    if playerok_bot is None:
        return None
    return getattr(playerok_bot, "account", None) or getattr(playerok_bot, "playerok_account", None)


async def _run(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


def _get_available() -> int | None:
    account = _get_account()
    if account is None:
        return None
    try:
        return int(account.get().profile.balance.available)
    except Exception:
        return None


async def start_withdrawal(callback: CallbackQuery, state: FSMContext):
    """Точка входа в вывод средств (вызывается из раздела Финансы)."""
    await state.set_state(None)
    await state.update_data(wd_provider=None, wd_account=None, wd_account_display=None,
                            wd_sbp_bank=None, wd_sbp_bank_name=None, wd_amount=None)
    available = _get_available()
    await throw_float_message(
        state=state,
        message=callback.message,
        text=templ.withdraw_method_text(available if available is not None else "—"),
        reply_markup=templ.withdraw_method_kb(),
        callback=callback,
    )


@router.callback_query(calls.WithdrawAction.filter())
async def callback_withdraw_action(callback: CallbackQuery, callback_data: calls.WithdrawAction, state: FSMContext):
    try:
        action = callback_data.action
        value = callback_data.value

        account = _get_account()
        if account is None:
            await callback.answer("❌ Аккаунт Playerok недоступен.", show_alert=True)
            return

        if action == "cancel":
            await state.set_state(None)
            await throw_float_message(
                state=state,
                message=callback.message,
                text=templ.finance_main_text(),
                reply_markup=templ.finance_main_kb(),
                callback=callback,
            )
            return

        if action == "provider":
            await state.set_state(None)
            await state.update_data(wd_provider=value)

            if value == "SBP":
                await state.set_state(states.WithdrawStates.waiting_for_sbp_phone)
                await throw_float_message(
                    state=state,
                    message=callback.message,
                    text=templ.withdraw_float_text("📱 Введите <b>номер телефона</b> получателя (в формате 79001234567) ↓"),
                    reply_markup=templ.back_kb(calls.FinanceNavigation(to="withdraw").pack()),
                    callback=callback,
                )
                return

            if value == "USDT":
                await state.set_state(states.WithdrawStates.waiting_for_usdt_address)
                await throw_float_message(
                    state=state,
                    message=callback.message,
                    text=templ.withdraw_float_text("🪙 Введите <b>адрес кошелька USDT (TRC20)</b> ↓"),
                    reply_markup=templ.back_kb(calls.FinanceNavigation(to="withdraw").pack()),
                    callback=callback,
                )
                return

            # Карты (BANK_CARD_RU / BANK_CARD_BY / BANK_CARD)
            card_list = await _run(account.get_verified_cards, count=CARDS_PAGE_SIZE)
            await throw_float_message(
                state=state,
                message=callback.message,
                text=templ.withdraw_cards_text(card_list),
                reply_markup=templ.withdraw_cards_kb(card_list),
                callback=callback,
            )
            return

        if action == "card":
            # Выбрана карта: value = card_id
            card_list = await _run(account.get_verified_cards, count=CARDS_PAGE_SIZE)
            card = next((c for c in getattr(card_list, "bank_cards", []) if c.id == value), None)
            display = f"••••{card.card_last_four}" if card else value
            await state.update_data(wd_account=value, wd_account_display=display)
            await _ask_amount(callback, state)
            return

        if action == "sbp_bank":
            # Выбран банк СБП: value = member_id
            members = await _run(account.get_sbp_bank_members)
            member = next((m for m in members if m.id == value), None)
            await state.update_data(wd_sbp_bank=value, wd_sbp_bank_name=(member.name if member else value))
            await _ask_amount(callback, state)
            return

        if action == "confirm":
            await _execute_withdrawal(callback, state, account)
            return

        await callback.answer("❌ Неизвестное действие.", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка вывода ({callback_data.action}): {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


async def _ask_amount(callback_or_message, state: FSMContext):
    await state.set_state(states.WithdrawStates.waiting_for_amount)
    available = _get_available()
    hint = f"\n┗ Доступно: <code>{available}₽</code>" if available is not None else ""
    text = templ.withdraw_float_text(f"💰 Введите <b>сумму вывода</b> (в рублях) ↓{hint}")
    kb = templ.back_kb(calls.FinanceNavigation(to="withdraw").pack())
    message = getattr(callback_or_message, "message", callback_or_message)
    callback = callback_or_message if hasattr(callback_or_message, "message") else None
    await throw_float_message(state=state, message=message, text=text, reply_markup=kb, callback=callback)


async def _show_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    provider = data.get("wd_provider")
    amount = int(data.get("wd_amount"))
    account_display = data.get("wd_account_display") or data.get("wd_account") or "—"
    extra = data.get("wd_sbp_bank_name") if provider == "SBP" else None
    await throw_float_message(
        state=state,
        message=message,
        text=templ.withdraw_confirm_text(provider, account_display, amount, extra),
        reply_markup=templ.withdraw_confirm_kb(),
    )


async def _execute_withdrawal(callback: CallbackQuery, state: FSMContext, account):
    data = await state.get_data()
    provider_name = data.get("wd_provider")
    account_value = data.get("wd_account")
    amount = data.get("wd_amount")
    sbp_bank = data.get("wd_sbp_bank")

    if not provider_name or not account_value or not amount:
        await callback.answer("❌ Данные вывода неполные, начните заново.", show_alert=True)
        return

    try:
        provider = TransactionProviderIds[provider_name]
    except Exception:
        await callback.answer("❌ Неверный провайдер вывода.", show_alert=True)
        return

    await state.set_state(None)
    try:
        await _run(
            account.request_withdrawal,
            provider,
            str(account_value),
            int(amount),
            None,
            sbp_bank if provider_name == "SBP" else None,
        )
        await throw_float_message(
            state=state,
            message=callback.message,
            text=templ.withdraw_float_text(f"✅ Запрос на вывод <b>{amount}₽</b> отправлен."),
            reply_markup=templ.back_kb(calls.FinanceNavigation(to="main").pack()),
            callback=callback,
        )
    except Exception as e:
        logger.error(f"Ошибка запроса вывода: {e}", exc_info=True)
        await throw_float_message(
            state=state,
            message=callback.message,
            text=templ.withdraw_float_text(f"❌ Не удалось вывести средства:\n<code>{e}</code>"),
            reply_markup=templ.back_kb(calls.FinanceNavigation(to="withdraw").pack()),
            callback=callback,
        )


# ВВОД ТЕКСТА (FSM)

@router.message(states.WithdrawStates.waiting_for_sbp_phone, F.text)
async def handler_sbp_phone(message: Message, state: FSMContext):
    try:
        phone = "".join(ch for ch in message.text.strip() if ch.isdigit())
        if len(phone) < 10:
            raise Exception("❌ Введите корректный номер телефона (например 79001234567)")

        await state.update_data(wd_account=phone, wd_account_display=phone)

        account = _get_account()
        members = await _run(account.get_sbp_bank_members)
        await state.set_state(None)
        await throw_float_message(
            state=state,
            message=message,
            text=templ.withdraw_sbp_banks_text(),
            reply_markup=templ.withdraw_sbp_banks_kb(members),
        )
    except Exception as e:
        await throw_float_message(
            state=state,
            message=message,
            text=templ.withdraw_float_text(str(e)),
            reply_markup=templ.back_kb(calls.FinanceNavigation(to="withdraw").pack()),
        )


@router.message(states.WithdrawStates.waiting_for_usdt_address, F.text)
async def handler_usdt_address(message: Message, state: FSMContext):
    try:
        address = message.text.strip()
        if len(address) < 20:
            raise Exception("❌ Введите корректный адрес кошелька USDT (TRC20)")

        await state.update_data(wd_account=address, wd_account_display=address)
        await _ask_amount(message, state)
    except Exception as e:
        await throw_float_message(
            state=state,
            message=message,
            text=templ.withdraw_float_text(str(e)),
            reply_markup=templ.back_kb(calls.FinanceNavigation(to="withdraw").pack()),
        )


@router.message(states.WithdrawStates.waiting_for_amount, F.text)
async def handler_amount(message: Message, state: FSMContext):
    try:
        raw = message.text.strip().replace(" ", "")
        if not raw.isdigit():
            raise Exception("❌ Введите сумму числом (например 1000)")
        amount = int(raw)
        if amount <= 0:
            raise Exception("❌ Сумма должна быть больше нуля")

        available = _get_available()
        if available is not None and amount > available:
            raise Exception(f"❌ Недостаточно средств. Доступно: {available}₽")

        await state.update_data(wd_amount=amount)
        await state.set_state(None)
        await _show_confirm(message, state)
    except Exception as e:
        await throw_float_message(
            state=state,
            message=message,
            text=templ.withdraw_float_text(str(e)),
            reply_markup=templ.back_kb(calls.FinanceNavigation(to="withdraw").pack()),
        )
