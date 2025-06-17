# This file provides mappings between province names in Chinese and Pinyin.

PROVINCE_PINYIN_MAP = {
    "重庆": "chongqing",
    "广东": "guangdong",
    "广西": "guangxi",
    "河北": "hebei",
    "湖北": "hubei",
    "江苏": "jiangsu",
    "山东": "shandong",
    "四川": "sichuan",
    "浙江": "zhejiang",
}

# Create the reverse mapping for efficient lookup
PINYIN_PROVINCE_MAP = {v: k for k, v in PROVINCE_PINYIN_MAP.items()}

def get_province_pinyin(pinyin_name: str) -> str:
    """
    Converts a pinyin province name to its Chinese equivalent.

    Args:
        pinyin_name: The province name in pinyin (e.g., "chongqing").

    Returns:
        The Chinese name of the province (e.g., "重庆"), or None if not found.
    """
    return PINYIN_PROVINCE_MAP.get(pinyin_name.lower())

def get_chinese_province_list() -> list:
    """Returns a list of all supported Chinese province names."""
    return list(PROVINCE_PINYIN_MAP.keys()) 