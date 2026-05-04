"""Widget key generation utilities."""

import secrets

WIDGET_KEY_PREFIX = "wk_"


def generate_widget_key() -> str:
    """Generate a unique publishable widget key.

    Returns:
        str: A widget key in the format 'wk_' + 24-char URL-safe random string.
    """
    return f"{WIDGET_KEY_PREFIX}{secrets.token_urlsafe(18)}"
