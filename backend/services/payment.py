"""
payment.py – BNPL (Buy Now Pay Later) / installment payment filter.
Parses shop payment_options to identify stores with credit purchase capability.
"""

import json

# Known BNPL providers in Iran
BNPL_PROVIDERS = {
    "اسنپ‌پی": {"name": "اسنپ‌پی", "color": "#00D170", "icon": "snappay"},
    "تارا": {"name": "تارا", "color": "#6C63FF", "icon": "tara"},
    "دیجی پی": {"name": "دیجی‌پی", "color": "#ED1C24", "icon": "digipay"},
    "ازکی‌وام": {"name": "ازکی‌وام", "color": "#FF6B00", "icon": "azki"},
    "ترب‌پی": {"name": "ترب‌پی", "color": "#E8453C", "icon": "torobpay"},
    "دکان ابزار": {"name": "دکان ابزار", "color": "#333", "icon": "dokan"},
    "جیتکس مارکت": {"name": "جیتکس مارکت", "color": "#0066CC", "icon": "jitex"},
}


def parse_payment_options(payment_options_str: str) -> list[dict]:
    """
    Parse payment_options JSON and return structured payment info.
    """
    if not payment_options_str or payment_options_str in ("null", "[]"):
        return []

    try:
        options = json.loads(payment_options_str)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(options, list):
        return []

    result = []
    for opt in options:
        if not isinstance(opt, dict):
            continue
        provider_name = opt.get("provider_name", "")
        channel = opt.get("channel", "unknown")
        result.append({
            "provider_name": provider_name,
            "channel": channel,
            "is_in_person": channel == "in_person" or channel == "unknown",
            "min_price_toman": opt.get("min_price_toman"),
            "max_price_toman": opt.get("max_price_toman"),
        })
    return result


def get_bnpl_providers(payment_options_str: str) -> list[str]:
    """
    Get list of BNPL provider names for a shop.
    Only includes providers that support in-person payments.
    """
    options = parse_payment_options(payment_options_str)
    providers = []
    for opt in options:
        name = opt["provider_name"]
        if name in BNPL_PROVIDERS and opt.get("is_in_person", True):
            providers.append(name)
    return providers


def has_bnpl(payment_options_str: str, provider: str = "") -> bool:
    """
    Check if a shop supports BNPL.
    If provider is specified, check for that specific provider.
    """
    providers = get_bnpl_providers(payment_options_str)
    if not providers:
        return False
    if provider:
        return provider in providers
    return True


def get_all_provider_names() -> list[str]:
    """Return list of all known BNPL provider names."""
    return list(BNPL_PROVIDERS.keys())


def get_provider_info(name: str) -> dict | None:
    """Get provider display info."""
    return BNPL_PROVIDERS.get(name)
