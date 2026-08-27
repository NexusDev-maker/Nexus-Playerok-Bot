"""
Автозамена данных в исходящих сообщениях бота.

Каждое правило хранится в настройке "data_replacements" и имеет вид:
{
    "enabled": true,
    "keyphrases": ["{gift}", "{promo}"],   # что искать в тексте
    "data": ["значение1", "значение2"]      # на что заменять
}

Если у правила несколько значений в "data" — при замене выбирается случайное.
Замена не расходует значения (текст просто подставляется).
"""
from __future__ import annotations

import random
from logging import getLogger

logger = getLogger("seal.data_replacement")


def normalize_data_replacements(raw) -> list[dict]:
    """Приводит список правил замены к корректному виду."""
    result: list[dict] = []
    if not isinstance(raw, list):
        return result

    for item in raw:
        if not isinstance(item, dict):
            continue
        keyphrases = [str(k) for k in item.get("keyphrases", []) if str(k).strip()]
        data = [str(d) for d in item.get("data", []) if str(d) != ""]
        result.append({
            "enabled": bool(item.get("enabled", True)),
            "keyphrases": keyphrases,
            "data": data,
        })
    return result


def apply_data_replacements(text: str | None, replacements: list[dict] | None) -> str | None:
    """
    Применяет правила автозамены к тексту.

    :param text: Исходный текст сообщения.
    :param replacements: Список правил (уже нормализованный или сырой).
    :return: Текст с применёнными заменами.
    """
    if not text or not replacements:
        return text

    try:
        rules = normalize_data_replacements(replacements)
        for rule in rules:
            if not rule.get("enabled", True):
                continue
            data = rule.get("data") or []
            if not data:
                continue
            for phrase in rule.get("keyphrases", []):
                if phrase and phrase in text:
                    value = data[0] if len(data) == 1 else random.choice(data)
                    text = text.replace(phrase, value)
    except Exception as e:
        logger.warning(f"Ошибка автозамены данных: {e}")

    return text
