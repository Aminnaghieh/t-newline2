"""
mall.py – Parse shop addresses to extract mall/passage, floor, unit info.
Provides indoor navigation guidance for Tehran shopping centers.
"""

import re

# Common mall/passage names in Tehran
KNOWN_MALLS = [
    "علاءالدین", "علالدین", "علاالدین",
    "چارسو", "پایتخت", "پالادیوم", "ایران مال", "ایرانمال",
    "کوروش", "تیراژه", "ارگ", "رضا", "گلدیس",
    "تندیس", "نور", "ملت", "میلاد نور",
    "اپال", "سام سنتر", "برج سفید",
    "مبعث", "جام جم", "بازار بزرگ", "گالریا",
    "الماس", "اطلس", "آفتاب", "آفریقا", "ونک",
    "ستاره فارس", "لاله‌زار", "امیرکبیر",
]

# Regex patterns for floor/unit extraction
FLOOR_PATTERNS = [
    r"طبقه\s*[:\-]?\s*(\-?\d+|همکف|زیرزمین|اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم)",
    r"ط\s*[:\-]?\s*(\-?\d+)",
]

UNIT_PATTERNS = [
    r"واحد\s*[:\-]?\s*(\d+[A-Za-z]?)",
    r"پلاک\s*[:\-]?\s*(\d+[A-Za-z]?)",
    r"(?:شماره|ش)\s*[:\-]?\s*(\d+)",
    r"مغازه\s*[:\-]?\s*(\d+[A-Za-z]?)",
]

HALLWAY_PATTERNS = [
    r"راهرو\s*[:\-]?\s*(\w+)",
    r"بلوک\s*[:\-]?\s*(\w+)",
]

PASSAGE_PATTERNS = [
    r"پاساژ\s+(\S+(?:\s+\d+)?)",
    r"مجتمع\s+(?:تجاری\s+)?(\S+(?:\s+\d+)?)",
    r"مرکز\s+(?:خرید|تجاری)\s+(\S+(?:\s+\d+)?)",
    r"بازارچه\s+(\S+)",
    r"پ(?:اساژ|\.)\s*(\S+(?:\s+\d+)?)",
]


def parse_mall_info(address: str) -> dict | None:
    """
    Extract mall/passage information from a shop address.
    Returns dict with mall_name, floor, unit, hallway, or None if not in a mall.
    """
    if not address:
        return None

    result = {
        "mall_name": "",
        "floor": "",
        "unit": "",
        "hallway": "",
        "raw_address": address,
    }

    found_mall = False

    # Check known malls
    for mall in KNOWN_MALLS:
        if mall in address:
            result["mall_name"] = mall
            found_mall = True
            break

    # Try passage patterns if no known mall found
    if not found_mall:
        for pattern in PASSAGE_PATTERNS:
            m = re.search(pattern, address)
            if m:
                result["mall_name"] = m.group(1).strip()
                found_mall = True
                break

    if not found_mall:
        return None

    # Extract floor
    for pattern in FLOOR_PATTERNS:
        m = re.search(pattern, address)
        if m:
            floor_raw = m.group(1)
            result["floor"] = _normalize_floor(floor_raw)
            break

    # Extract unit/plaque
    for pattern in UNIT_PATTERNS:
        m = re.search(pattern, address)
        if m:
            result["unit"] = m.group(1).strip()
            break

    # Extract hallway
    for pattern in HALLWAY_PATTERNS:
        m = re.search(pattern, address)
        if m:
            result["hallway"] = m.group(1).strip()
            break

    return result


def _normalize_floor(floor_str: str) -> str:
    """Normalize floor names to a consistent format."""
    floor_map = {
        "همکف": "همکف",
        "زیرزمین": "زیرزمین",
        "اول": "۱",
        "دوم": "۲",
        "سوم": "۳",
        "چهارم": "۴",
        "پنجم": "۵",
        "ششم": "۶",
        "هفتم": "۷",
        "هشتم": "۸",
        "نهم": "۹",
        "دهم": "۱۰",
    }
    if floor_str in floor_map:
        return floor_map[floor_str]
    return floor_str


def generate_mall_guide(mall_info: dict) -> str:
    """
    Generate a user-friendly indoor navigation guide in Persian.
    """
    if not mall_info or not mall_info.get("mall_name"):
        return ""

    parts = [f"📍 پاساژ/مرکز خرید {mall_info['mall_name']}"]

    if mall_info.get("floor"):
        floor_display = mall_info["floor"]
        if floor_display.lstrip("-").isdigit():
            floor_num = int(floor_display)
            if floor_num < 0:
                parts.append(f"🔽 زیرزمین {abs(floor_num)}")
            elif floor_num == 0:
                parts.append("▶️ طبقه همکف")
            else:
                parts.append(f"🔼 طبقه {floor_display}")
        else:
            parts.append(f"▶️ طبقه {floor_display}")

    if mall_info.get("hallway"):
        parts.append(f"↪️ راهرو {mall_info['hallway']}")

    if mall_info.get("unit"):
        parts.append(f"🚪 واحد/پلاک {mall_info['unit']}")

    return " ← ".join(parts)


def is_same_mall(address1: str, address2: str) -> bool:
    """Check if two addresses are in the same mall/passage."""
    m1 = parse_mall_info(address1)
    m2 = parse_mall_info(address2)
    if m1 and m2 and m1["mall_name"] and m2["mall_name"]:
        return m1["mall_name"] == m2["mall_name"]
    return False
