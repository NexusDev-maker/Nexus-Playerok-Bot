import textwrap
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from settings import Settings as sett

from .. import callback_datas as calls


def settings_watermark_text():
    config = sett.get("config")
    watermark_enabled = "🟢 Включено" if config["playerok"]["watermark"]["enabled"] else "🔴 Выключено"
    watermark_value = config["playerok"]["watermark"]["value"] or "❌ Не задано"
    
    txt = textwrap.dedent(f"""
        ⚙️ <b>Настройки → ©️ Водяной знак</b>

        ©️ <b>Водяной знак под сообщениями:</b> {watermark_enabled}
        ✍️©️ <b>Текст водяного знака:</b> {watermark_value}

        <b>Что такое водяной знак?</b>
        Водяной знак - это текст, который автоматически добавляется в конец всех отправляемых сообщений. Это может быть полезно для брендирования или добавления дополнительной информации.

        Выберите параметр для изменения ↓
    """)
    return txt


def settings_watermark_kb():
    config = sett.get("config")
    watermark_enabled = "🟢 Включено" if config["playerok"]["watermark"]["enabled"] else "🔴 Выключено"
    watermark_value = config["playerok"]["watermark"]["value"] or "❌ Не задано"
    
    rows = [
        [InlineKeyboardButton(text=f"©️ Водяной знак: {watermark_enabled}", callback_data="switch_watermark_enabled")],
        [InlineKeyboardButton(text=f"✍️©️ Изменить текст", callback_data="enter_watermark_value")],
        [InlineKeyboardButton(text=f"🎨 Выбрать шаблон", callback_data="watermark_presets")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    return kb


def settings_watermark_float_text(placeholder: str):
    txt = textwrap.dedent(f"""
        ⚙️ <b>Настройки → ©️ Водяной знак</b>
        \n{placeholder}
    """)
    return txt


# Фирменные шаблоны водяного знака (разными шрифтами)
WATERMARK_PRESETS = [
    "🦅 NexusPlayerok",
    "🦅 𝐍𝐞𝐱𝐮𝐬𝐏𝐥𝐚𝐲𝐞𝐫𝐨𝐤",
    "🦅 𝗡𝗲𝘅𝘂𝘀𝗣𝗹𝗮𝘆𝗲𝗿𝗼𝗸",
    "🦅 𝑵𝒆𝒙𝒖𝒔𝑷𝒍𝒂𝒚𝒆𝒓𝒐𝒌",
    "🦅 𝙽𝚎𝚡𝚞𝚜𝙿𝚕𝚊𝚢𝚎𝚛𝚘𝚔",
    "🦅 𝔑𝔢𝔵𝔲𝔰𝔓𝔩𝔞𝔶𝔢𝔯𝔬𝔨",
    "🦅 𝓝𝓮𝔁𝓾𝓼𝓟𝓵𝓪𝔂𝓮𝓻𝓸𝓴",
    "🦅 𝑁𝑒𝑥𝑢𝑠𝑃𝑙𝑎𝑦𝑒𝑟𝑜𝑘",
]


def watermark_presets_text():
    config = sett.get("config")
    current_watermark = config["playerok"]["watermark"]["value"] or "❌ Не задано"

    txt = textwrap.dedent(f"""
        🎨 <b>Водяной знак — выбор варианта</b>

        Текущий: <code>{current_watermark}</code>

        Выберите вариант из списка ниже — он будет писаться сверху ваших сообщений на Playerok.

        ✍️ Чтобы задать <b>свой</b> текст — нажмите «Изменить текст».
        🧹 Чтобы <b>убрать</b> водяной знак — отправьте <code>-</code>.
    """)
    return txt


def watermark_presets_kb():
    rows = []
    for index, value in enumerate(WATERMARK_PRESETS):
        rows.append([InlineKeyboardButton(text=value, callback_data=calls.WatermarkPreset(index=index).pack())])

    rows.append([InlineKeyboardButton(text="✍️ Изменить текст", callback_data="enter_watermark_value")])
    rows.append([InlineKeyboardButton(text="🧹 Убрать водяной знак", callback_data="watermark_disable")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=calls.SettingsNavigation(to="watermark").pack())])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    return kb
