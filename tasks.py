import sqlite3

import requests
from celery import Celery


REQUEST_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
}
BRAPI_QUOTE_URL = 'https://brapi.dev/api/quote/{symbol}'

app = Celery(
    main='tasks',
    broker='pyamqp://guest@localhost//',
    backend='db+sqlite:///celery.sqlite',
)


def normalize_symbol(stock_name: str) -> str:
    return stock_name.strip().upper().removesuffix('.SA')


def extract_price(payload: dict) -> float:
    results = payload.get('results') or []
    if not results:
        raise RuntimeError('Brapi retornou resposta sem cotacao.')

    price = results[0].get('regularMarketPrice')
    if price is None:
        raise RuntimeError('Nao foi possivel localizar o preco da acao no JSON.')

    return float(price)


def fetch_stock_price(stock_name: str) -> tuple[str, float]:
    symbol = normalize_symbol(stock_name)
    url = BRAPI_QUOTE_URL.format(symbol=symbol)

    response = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
    response.raise_for_status()

    return symbol, extract_price(response.json())


@app.task
def get_stock_price(stock_name: str) -> float:
    try:
        symbol, price = fetch_stock_price(stock_name)
    except requests.RequestException as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 429:
            raise RuntimeError('Brapi recusou a requisicao por excesso de chamadas.') from exc
        raise RuntimeError('Falha ao buscar a cotacao na Brapi.') from exc

    with sqlite3.connect('stocks.db') as conn:
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS STOCKS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_name TEXT,
            price REAL,
            moment DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        INSERT INTO STOCKS (stock_name, price)
        VALUES (?, ?)
        ''', (symbol, price))

        conn.commit()

    return price
