def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper().removesuffix('.SA')
    if not normalized:
        raise ValueError('Symbol must not be empty.')
    return normalized


def validate_threshold_price(value: float) -> float:
    if value <= 0:
        raise ValueError('target_price must be greater than zero.')
    return value
