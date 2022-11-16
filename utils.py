def trim_string(s: str, limit: int, ellips='…') -> str:
    s = s.strip()
    if len(s) > limit:
        return s[:limit - 1].strip() + ellips
    return s
