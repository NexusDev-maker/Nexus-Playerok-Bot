"""Проверка целостности бренда бота."""

_ORIGINAL = {
    "BOT_NAME": "Nexus Playerok Bot",
    "DEVELOPER": "@inboxper",
    "TELEGRAM_CHANNEL": "https://t.me/NexusPlayerok",
    "TELEGRAM_CHAT": "https://t.me/inboxper",
}

TAMPER_MESSAGE = (
    "🦅 <b>Айай, негодяй!!</b> 😜\n\n"
    "Ты поменял данные на свои... поменяй обратно ) \n"
    "Оригинал: <b>@NexusPlayerok</b>"
)


def is_brand_changed() -> bool:
    """True, если контакты/название бренда изменены относительно оригинала."""
    try:
        import __init__ as meta
    except Exception:
        return False
    for key, original in _ORIGINAL.items():
        if str(getattr(meta, key, "")) != original:
            return True
    return False
