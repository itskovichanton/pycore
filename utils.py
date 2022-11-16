def trim_string(s: str, limit: int, ellips='…') -> str:
    if not s:
        return ""
    s = s.strip()
    if len(s) > limit:
        return s[:limit - 1].strip() + ellips
    return s
