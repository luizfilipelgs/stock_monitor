import logging

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .brapi import QuoteLookupError, fetch_current_prices
from .config import get_settings
from .db import init_db, session_scope
from .models import Alert, AlertState, Stock, StockPrice, TriggerType, TriggeredAlert


logger = logging.getLogger(__name__)
settings = get_settings()

app = Celery('stock_monitor', broker=settings.broker_url)
app.conf.update(
    timezone=settings.celery_timezone,
    enable_utc=False,
    task_ignore_result=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        'collect-active-stock-prices-every-minute': {
            'task': 'tasks.collect_active_stock_prices',
            'schedule': crontab(minute='*'),
        },
    },
)

init_db()


def evaluate_alert_state(price: float, alert: Alert) -> AlertState:
    if alert.min_price is not None and price < alert.min_price:
        return AlertState.BELOW_MIN
    if alert.max_price is not None and price > alert.max_price:
        return AlertState.ABOVE_MAX
    return AlertState.NORMAL


def build_trigger_message(symbol: str, alert: Alert, price: float, state: AlertState) -> str:
    if state == AlertState.BELOW_MIN:
        return (
            f'{symbol} is below the configured minimum '
            f'({price:.2f} < {alert.min_price:.2f}).'
        )
    return (
        f'{symbol} is above the configured maximum '
        f'({price:.2f} > {alert.max_price:.2f}).'
    )


def build_trigger_type(state: AlertState) -> TriggerType:
    if state == AlertState.BELOW_MIN:
        return TriggerType.BELOW_MIN
    return TriggerType.ABOVE_MAX


@app.task(name='tasks.collect_active_stock_prices')
def collect_active_stock_prices() -> dict[str, int]:
    init_db()

    processed_stocks = 0
    triggered_alerts = 0
    failed_quotes = 0

    with session_scope() as db:
        stocks = list(
            db.scalars(
                select(Stock)
                .options(selectinload(Stock.alerts))
                .where(Stock.active.is_(True))
                .order_by(Stock.id)
            ).all()
        )

        if not stocks:
            return {
                'processed_stocks': processed_stocks,
                'triggered_alerts': triggered_alerts,
                'failed_quotes': failed_quotes,
            }

        try:
            price_by_symbol = fetch_current_prices([stock.symbol for stock in stocks])
        except QuoteLookupError as exc:
            logger.error('Failed to collect quotes for active stocks: %s', exc)
            return {
                'processed_stocks': processed_stocks,
                'triggered_alerts': triggered_alerts,
                'failed_quotes': len(stocks),
            }

        for stock in stocks:
            symbol = stock.symbol
            price = price_by_symbol.get(symbol)
            if price is None:
                failed_quotes += 1
                logger.error('No quote returned for %s in the batched Brapi response.', symbol)
                continue

            try:
                db.add(StockPrice(stock_id=stock.id, price=price))

                for alert in stock.alerts:
                    if not alert.active:
                        continue

                    new_state = evaluate_alert_state(price, alert)
                    previous_state = alert.current_state

                    if new_state == AlertState.NORMAL:
                        alert.current_state = AlertState.NORMAL
                        continue

                    if previous_state != new_state:
                        message = build_trigger_message(symbol, alert, price, new_state)
                        db.add(
                            TriggeredAlert(
                                alert_id=alert.id,
                                stock_id=stock.id,
                                price=price,
                                trigger_type=build_trigger_type(new_state),
                                message=message,
                            )
                        )
                        triggered_alerts += 1
                        logger.info(
                            'Triggered alert for %s | alert_id=%s | trigger_type=%s | price=%.2f | message=%s',
                            symbol,
                            alert.id,
                            new_state.value,
                            price,
                            message,
                        )

                    alert.current_state = new_state

                db.commit()
                processed_stocks += 1
            except Exception:
                db.rollback()
                logger.exception('Failed to persist monitoring cycle for %s.', stock.symbol)

    return {
        'processed_stocks': processed_stocks,
        'triggered_alerts': triggered_alerts,
        'failed_quotes': failed_quotes,
    }
