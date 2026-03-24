"""Telegram notifications – delegates to telegram_bot module."""
from app.telegram_bot import notify_success, notify_error

__all__ = ["notify_success", "notify_error"]
