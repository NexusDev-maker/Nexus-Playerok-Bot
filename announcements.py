"""
Система рассылки объявлений.
Получает объявление (announcement.json) из GitHub-репозитория разработчика
и рассылает его владельцу(ам) каждой запущенной копии бота.

Рассылку контролирует только тот, у кого есть доступ к репозиторию:
достаточно изменить файл announcement.json (в частности поле "tag"),
и все копии бота покажут новое сообщение своим владельцам.

Формат announcement.json:
{
    "tag": "2024-06-01-1",          // уникальная метка; меняй её при новой рассылке
    "text": "Текст сообщения",       // поддерживает HTML
    "photo": "https://.../pic.png",  // опционально, ссылка на картинку
    "pin": false,                     // опционально, закрепить сообщение
    "buttons": [                      // опционально, кнопки-ссылки
        {"text": "Канал", "url": "https://t.me/..."}
    ]
}
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from logging import getLogger
import requests
import json
import os

# Импорт путей из центрального модуля
import paths
from __init__ import REPO, ANNOUNCEMENT_BRANCH, ANNOUNCEMENT_FILE, REPO_CONFIGURED

if TYPE_CHECKING:
    from tgbot.telegrambot import TelegramBot

logger = getLogger("seal.announcements")


REQUESTS_DELAY = 600  # 10 минут

# Ссылка на файл рассылки в репозитории разработчика.
ANNOUNCEMENT_URL = (
    f"https://raw.githubusercontent.com/{REPO}/{ANNOUNCEMENT_BRANCH}/{ANNOUNCEMENT_FILE}"
)


def get_cache_path() -> str:
    """Возвращает путь к файлу кэша."""
    os.makedirs(paths.CACHE_DIR, exist_ok=True)
    return paths.ANNOUNCEMENT_TAG_FILE


def get_last_tag() -> str | None:
    """
    Загружает тег последнего объявления из кэша.

    :return: тег последнего объявления или None
    """
    cache_path = get_cache_path()
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="UTF-8") as f:
            return f.read().strip()
    except:
        return None


def save_last_tag(tag: str):
    """
    Сохраняет тег последнего объявления в кэш.

    :param tag: тег объявления
    """
    cache_path = get_cache_path()
    try:
        with open(cache_path, "w", encoding="UTF-8") as f:
            f.write(tag)
    except Exception as e:
        logger.error(f"Ошибка сохранения тега объявления: {e}")


LAST_TAG = get_last_tag()


def get_announcement(ignore_last_tag: bool = False) -> dict | None:
    """
    Получает объявление из файла announcement.json в GitHub-репозитории.

    :param ignore_last_tag: игнорировать сохранённый тег
    :return: словарь с данными объявления или None
    """
    global LAST_TAG

    headers = {
        "User-Agent": "PlayerokBot-Announcements",
        "Accept": "application/json",
        # обходим кэш CDN, чтобы новая рассылка доходила быстрее
        "Cache-Control": "no-cache",
    }

    try:
        response = requests.get(
            ANNOUNCEMENT_URL,
            headers=headers,
            timeout=10,
        )

        # 404 = файла рассылки нет в репозитории (это нормально: рассылок пока нет)
        if response.status_code != 200:
            return None

        content = json.loads(response.text)
        if not isinstance(content, dict):
            return None

        # Проверяем тег: если он не менялся — рассылать повторно не нужно
        if content.get("tag") == LAST_TAG and not ignore_last_tag:
            return None

        return content

    except Exception as e:
        logger.debug(f"Не удалось получить объявление: {e}")
        return None


def download_photo(url: str) -> bytes | None:
    """
    Загружает фото по URL.

    :param url: URL фотографии
    :return: фотографию в байтах или None
    """
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.content
    except:
        pass
    return None


def get_text(data: dict) -> str | None:
    """Получает текст объявления."""
    return data.get("text")


def get_photo_bytes(data: dict) -> bytes | None:
    """Получает фото объявления."""
    photo_url = data.get("photo")
    if photo_url:
        return download_photo(photo_url)
    return None


def get_pin(data: dict) -> bool:
    """Нужно ли закреплять сообщение."""
    return bool(data.get("pin", False))


def get_buttons(data: dict) -> list | None:
    """
    Получает кнопки для клавиатуры.
    Формат: [{"text": "Кнопка", "url": "https://..."}]
    """
    return data.get("buttons")


async def send_announcement_to_users(tg_bot: TelegramBot, data: dict):
    """
    Отправляет объявление всем авторизованным пользователям.

    :param tg_bot: экземпляр Telegram бота
    :param data: данные объявления
    """
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from settings import Settings as sett

    text = get_text(data)
    photo = get_photo_bytes(data)
    pin = get_pin(data)
    buttons_data = get_buttons(data)

    if not text and not photo:
        return

    # Формируем клавиатуру
    keyboard = None
    if buttons_data:
        rows = []
        for btn in buttons_data:
            if btn.get("text") and btn.get("url"):
                rows.append([InlineKeyboardButton(
                    text=btn["text"],
                    url=btn["url"]
                )])
        if rows:
            keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    # Получаем список пользователей
    config = sett.get("config")
    users = config["telegram"]["bot"].get("signed_users", [])

    logger.info(f"📢 Отправка объявления {len(users)} пользователям...")

    for user_id in users:
        try:
            if photo:
                msg = await tg_bot.bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                msg = await tg_bot.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )

            # Закрепляем если нужно
            if pin and msg:
                try:
                    await tg_bot.bot.pin_chat_message(
                        chat_id=user_id,
                        message_id=msg.message_id,
                        disable_notification=True
                    )
                except:
                    pass

            logger.info(f"✅ Объявление отправлено пользователю {user_id}")

        except Exception as e:
            logger.warning(f"❌ Не удалось отправить объявление пользователю {user_id}: {e}")

        # Небольшая задержка между отправками
        await asyncio.sleep(0.1)


async def check_and_send_announcement(tg_bot: TelegramBot, ignore_last_tag: bool = False):
    """
    Проверяет наличие нового объявления и отправляет его.

    :param tg_bot: экземпляр Telegram бота
    :param ignore_last_tag: игнорировать сохранённый тег
    """
    global LAST_TAG

    data = get_announcement(ignore_last_tag=ignore_last_tag)
    if not data:
        return

    # Если это первый запуск - просто сохраняем тег
    if not LAST_TAG and not ignore_last_tag:
        LAST_TAG = data.get("tag", "")
        save_last_tag(LAST_TAG)
        return

    # Сохраняем новый тег
    if not ignore_last_tag:
        LAST_TAG = data.get("tag", "")
        save_last_tag(LAST_TAG)

    # Отправляем объявление
    await send_announcement_to_users(tg_bot, data)


import asyncio

async def announcements_loop(tg_bot: TelegramBot):
    """
    Бесконечный цикл проверки объявлений.

    :param tg_bot: экземпляр Telegram бота
    """
    if not REPO_CONFIGURED:
        return

    logger.debug(f"Система объявлений запущена (источник: {ANNOUNCEMENT_URL})")

    while True:
        try:
            await check_and_send_announcement(tg_bot)
        except Exception as e:
            logger.error(f"Ошибка в цикле объявлений: {e}")

        await asyncio.sleep(REQUESTS_DELAY)


async def start_announcements_loop(tg_bot: TelegramBot):
    """
    Запускает цикл проверки объявлений как asyncio task в текущем event loop.

    :param tg_bot: экземпляр Telegram бота
    """
    asyncio.create_task(announcements_loop(tg_bot))


