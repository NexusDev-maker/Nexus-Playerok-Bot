import textwrap
from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .. import callback_datas as calls


def _format_date(raw: str | None) -> str:
    if not raw:
        return "—"
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(raw)


def _stars(rating) -> str:
    try:
        rating = int(rating)
    except Exception:
        rating = 0
    rating = max(0, min(5, rating))
    return "⭐" * rating + "☆" * (5 - rating)


def reviews_text(review_list, page: int) -> str:
    reviews = getattr(review_list, "reviews", []) or []
    if not reviews:
        return textwrap.dedent("""
            ⭐ <b>Отзывы</b>

            Пока нет ни одного отзыва.
        """).strip()

    lines = ["⭐ <b>Отзывы</b>", f"<i>Страница {page + 1}</i>", ""]
    for rev in reviews:
        creator = getattr(rev, "creator", None)
        username = getattr(creator, "username", None) or "Пользователь"
        date = _format_date(getattr(rev, "created_at", None))
        text = getattr(rev, "text", None) or "<i>без текста</i>"

        lines.append(f"{_stars(getattr(rev, 'rating', 0))}  <b>{username}</b>")
        lines.append(f"  ┣ {text}")
        lines.append(f"  ┗ 🕒 {date}")
        lines.append("")

    return "\n".join(lines).strip()


def reviews_kb(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    nav_row = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=calls.ReviewsAction(action="prev").pack()))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}", callback_data="page_info"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="➡️ Далее", callback_data=calls.ReviewsAction(action="next").pack()))

    return InlineKeyboardMarkup(inline_keyboard=[
        nav_row,
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=calls.ReviewsAction(action="refresh").pack())],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=calls.MenuPagination(page=1).pack())],
    ])
