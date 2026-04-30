# Monitor de Acoes com Alertas Simples

Async stock monitoring system built with FastAPI, Celery, RabbitMQ and Flower.
It allows users to register stocks with min/max price alerts, periodically fetches
stock prices from Brapi, stores price history and logs triggered alerts.

## Stack

- FastAPI
- Celery
- RabbitMQ
- Celery Beat
- Flower
- SQLite
- SQLAlchemy

## Run with Docker Compose

```bash
docker compose up --build
```

## Brapi test limitation

Without a `BRAPI_TOKEN`, this project depends on Brapi's free test symbols only.
For local tests without token, use one of these stocks:

- `PETR4`
- `MGLU3`
- `VALE3`
- `ITUB4`

If you try other symbols without a token, Brapi may reject the request or return
an empty result.

If you want broader Brapi access or higher limits, export `BRAPI_TOKEN` before
starting the stack:

```bash
export BRAPI_TOKEN=your_token_here
docker compose up --build
```

## Useful URLs

- Swagger: `http://localhost:8000/docs`
- RabbitMQ Management: `http://localhost:15672`
- Flower: `http://localhost:5555`

RabbitMQ credentials:

- User: `guest`
- Password: `guest`

## API overview

### Stocks

- `POST /stocks`
- `GET /stocks`
- `GET /stocks/{stock_id}`
- `PATCH /stocks/{stock_id}`
- `DELETE /stocks/{stock_id}`
- `GET /stocks/{stock_id}/prices`
- `GET /stocks/{stock_id}/triggered-alerts`

### Alerts

- `POST /stocks/{stock_id}/alerts`
- `GET /stocks/{stock_id}/alerts`
- `PATCH /alerts/{alert_id}`
- `DELETE /alerts/{alert_id}`

### Example stock payload

```json
{
  "symbol": "PETR4",
  "active": true
}
```

### Example alert batch payload

```json
[
  {
    "min_price": 35.0,
    "max_price": 40.0,
    "active": true
  },
  {
    "min_price": 32.0,
    "max_price": 45.0,
    "active": true
  }
]
```
