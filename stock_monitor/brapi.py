import requests

from .config import get_settings
from .utils import normalize_symbol


REQUEST_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
}


class QuoteLookupError(RuntimeError):
    pass


def build_request_headers() -> dict[str, str]:
    settings = get_settings()
    headers = dict(REQUEST_HEADERS)
    if settings.brapi_token:
        headers['Authorization'] = f'Bearer {settings.brapi_token}'
    return headers


def fetch_current_prices(symbols: list[str]) -> dict[str, float]:
    normalized_symbols = [normalize_symbol(symbol) for symbol in symbols]
    if not normalized_symbols:
        return {}

    settings = get_settings()
    tickers = ','.join(normalized_symbols)
    url = f'{settings.brapi_base_url}/quote/{tickers}'

    try:
        response = requests.get(url, headers=build_request_headers(), timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise QuoteLookupError(f'Failed to fetch quotes for {tickers}.') from exc

    payload = response.json()
    results = payload.get('results') or []
    if not results:
        raise QuoteLookupError(f'Brapi returned an empty quote payload for {tickers}.')

    prices: dict[str, float] = {}
    for result in results:
        symbol = result.get('symbol')
        price = result.get('regularMarketPrice')
        if not symbol or price is None:
            continue
        prices[normalize_symbol(symbol)] = float(price)

    if not prices:
        raise QuoteLookupError(f'Brapi did not return any usable regularMarketPrice for {tickers}.')

    return prices
