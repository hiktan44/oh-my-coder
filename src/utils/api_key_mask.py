"""
API Key maskelearac

saglar API Key maskeleislev, kacinicindelog, hata mesajiicindesizintihassasbilgi. 
"""

import re
from typing import Optional

# sikgor API Key mod
API_KEY_PATTERNS = [
    # OpenAI / DeepSeek / Zhipu AI vb. (sk-...)
    (r"(sk-[a-zA-Z0-9]{4})[a-zA-Z0-9]{4,}([a-zA-Z0-9]{4})", r"\1....\2"),
    # Bearer Token
    (r"(Bearer\s+[a-zA-Z0-9]{4})[a-zA-Z0-9]{4,}([a-zA-Z0-9]{4})", r"\1....\2"),
    # ZHIPUAI_API_KEY (zai-...)
    (r"(zai-[a-zA-Z0-9]{4})[a-zA-Z0-9]{4,}([a-zA-Z0-9]{4})", r"\1....\2"),
    # kullan API Key (kadaraz8karakter, harfanasayiharf+azmiktarozelkarakter)
    (r"([a-zA-Z0-9]{4})[a-zA-Z0-9+/=_-]{4,}([a-zA-Z0-9]{4})", r"\1....\2"),
]


def mask_api_key(text: str, mask_char: str = "....") -> str:
    """
    icinmetinicinde API Key ilerlesatirmaskeleisle. 

    Args:
        text: hammetin (olabiliredebiliricerir API Key) 
        mask_char: maskeledegistirkarakter, varsayilan "...."

    Returns:
        maskelesonrametin

    Examples:
        >>> mask_api_key("my key is sk-abc123def456")
        'my key is sk-ab....56'
        >>> mask_api_key("ZHIPUAI_API_KEY=zai-1234567890abcdef")
        'ZHIPUAI_API_KEY=zai-1....def'
    """
    if not text:
        return text

    result = text
    for pattern, replacement in API_KEY_PATTERNS:
        result = re.sub(pattern, replacement, result)

    return result


def mask_headers(headers: dict) -> dict:
    """
    icin HTTP Headers icindehassasbilgiilerlesatirmaskele. 

    Args:
        headers: HTTP Headers sozluk

    Returns:
        maskelesonra Headers sozluk

    Examples:
        >>> mask_headers({"Authorization": "Bearer sk-abc123"})
        {'Authorization': 'Bearer sk-....'}
    """
    if not headers:
        return headers

    masked = headers.copy()
    sensitive_keys = ["authorization", "x-api-key", "api-key", "token"]

    for key in masked:
        if key.lower() in sensitive_keys:
            masked[key] = mask_api_key(masked[key])

    return masked


def safe_log(message: str, logger_func, *args, **kwargs) -> None:
    """
    guvenliklogkayitfonksiyon, otomatikmaskele API Key. 

    Args:
        message: logmesaj (olabiliredebiliricerir API Key) 
        logger_func: logfonksiyon (ornegin logger.info, logger.debug) 
        *args, **kwargs: iletiletver logger_func parametre
    """
    masked_message = mask_api_key(message)
    logger_func(masked_message, *args, **kwargs)


class APIKeyMasker:
    """
    API Key maskele (sinifsurum, destekozelkural) . 
    """

    def __init__(self, custom_patterns: Optional[list] = None) -> None:
        """
        Args:
            custom_patterns: ozelmaskelekural, formaticin [(pattern, replacement), ...]
        """
        self.patterns = custom_patterns if custom_patterns else API_KEY_PATTERNS

    def mask(self, text: str) -> str:
        """maskelemetinicinde API Key"""
        if not text:
            return text

        result = text
        for pattern, replacement in self.patterns:
            result = re.sub(pattern, replacement, result)

        return result

    def mask_dict(self, data: dict, keys_to_mask: Optional[list] = None) -> dict:
        """
        maskelesozlukicindehassasalan. 

        Args:
            data: hamsozluk
            keys_to_mask: gerekistermaskeleanahtarliste, varsayilan ["api_key", "token", "password"]
        """
        if not data:
            return data

        masked = data.copy()
        keys_to_mask = keys_to_mask or ["api_key", "token", "password", "secret"]

        for key in masked:
            if key.lower() in [k.lower() for k in keys_to_mask]:
                if isinstance(masked[key], str):
                    masked[key] = self.mask(masked[key])

        return masked
