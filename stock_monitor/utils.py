def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper().removesuffix('.SA')
    if not normalized:
        raise ValueError('Symbol must not be empty.')
    return normalized


def validate_alert_bounds(min_price: float | None, max_price: float | None) -> None:
    if min_price is None and max_price is None:
        raise ValueError('At least one of min_price or max_price must be provided.')

    if min_price is not None and max_price is not None and min_price >= max_price:
        raise ValueError('min_price must be lower than max_price.')
