from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .db import get_db, init_db
from .models import Alert, AlertState, Stock, StockPrice, TriggeredAlert
from .schemas import (
    AlertCreate,
    AlertRead,
    AlertUpdate,
    StockCreate,
    StockDetailRead,
    StockPriceRead,
    StockRead,
    StockUpdate,
    TriggeredAlertRead,
)
from .utils import validate_alert_bounds


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title='Monitor de Acoes com Alertas Simples',
    version='1.0.0',
    lifespan=lifespan,
)


def get_stock_or_404(db: Session, stock_id: int) -> Stock:
    stock = db.get(Stock, stock_id)
    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Stock not found.')
    return stock


def get_alert_or_404(db: Session, alert_id: int) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Alert not found.')
    return alert


@app.post('/stocks', response_model=StockRead, status_code=status.HTTP_201_CREATED)
def create_stock(payload: StockCreate, db: Session = Depends(get_db)) -> Stock:
    existing_stock = db.scalar(select(Stock).where(Stock.symbol == payload.symbol))
    if existing_stock is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Stock already exists.')

    stock = Stock(symbol=payload.symbol, active=payload.active)
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


@app.get('/stocks', response_model=list[StockRead])
def list_stocks(db: Session = Depends(get_db)) -> list[Stock]:
    return list(db.scalars(select(Stock).order_by(Stock.id)).all())


@app.get('/stocks/{stock_id}', response_model=StockDetailRead)
def get_stock(stock_id: int, db: Session = Depends(get_db)) -> Stock:
    stock = db.scalar(
        select(Stock)
        .options(selectinload(Stock.alerts))
        .where(Stock.id == stock_id)
    )
    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Stock not found.')
    return stock


@app.patch('/stocks/{stock_id}', response_model=StockRead)
def update_stock(stock_id: int, payload: StockUpdate, db: Session = Depends(get_db)) -> Stock:
    stock = get_stock_or_404(db, stock_id)

    if payload.symbol is not None and payload.symbol != stock.symbol:
        duplicate = db.scalar(select(Stock).where(Stock.symbol == payload.symbol))
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Stock already exists.')
        stock.symbol = payload.symbol
        for alert in stock.alerts:
            alert.current_state = AlertState.NORMAL

    if payload.active is not None:
        stock.active = payload.active

    db.commit()
    db.refresh(stock)
    return stock


@app.delete('/stocks/{stock_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_stock(stock_id: int, db: Session = Depends(get_db)) -> Response:
    stock = get_stock_or_404(db, stock_id)
    db.delete(stock)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post('/stocks/{stock_id}/alerts', response_model=list[AlertRead], status_code=status.HTTP_201_CREATED)
def create_alerts(stock_id: int, payload: list[AlertCreate], db: Session = Depends(get_db)) -> list[Alert]:
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Alert payload must not be empty.')

    stock = get_stock_or_404(db, stock_id)
    alerts: list[Alert] = []

    for item in payload:
        alert = Alert(
            stock_id=stock.id,
            min_price=item.min_price,
            max_price=item.max_price,
            active=item.active,
            current_state=AlertState.NORMAL,
        )
        alerts.append(alert)
        db.add(alert)

    db.commit()

    for alert in alerts:
        db.refresh(alert)

    return alerts


@app.get('/stocks/{stock_id}/alerts', response_model=list[AlertRead])
def list_stock_alerts(stock_id: int, db: Session = Depends(get_db)) -> list[Alert]:
    get_stock_or_404(db, stock_id)
    return list(
        db.scalars(
            select(Alert)
            .where(Alert.stock_id == stock_id)
            .order_by(Alert.id)
        ).all()
    )


@app.get('/stocks/{stock_id}/prices', response_model=list[StockPriceRead])
def list_stock_prices(stock_id: int, db: Session = Depends(get_db)) -> list[StockPrice]:
    get_stock_or_404(db, stock_id)
    return list(
        db.scalars(
            select(StockPrice)
            .where(StockPrice.stock_id == stock_id)
            .order_by(StockPrice.collected_at.desc(), StockPrice.id.desc())
        ).all()
    )


@app.get('/stocks/{stock_id}/triggered-alerts', response_model=list[TriggeredAlertRead])
def list_triggered_alerts(stock_id: int, db: Session = Depends(get_db)) -> list[TriggeredAlert]:
    get_stock_or_404(db, stock_id)
    return list(
        db.scalars(
            select(TriggeredAlert)
            .where(TriggeredAlert.stock_id == stock_id)
            .order_by(TriggeredAlert.triggered_at.desc(), TriggeredAlert.id.desc())
        ).all()
    )


@app.patch('/alerts/{alert_id}', response_model=AlertRead)
def update_alert(alert_id: int, payload: AlertUpdate, db: Session = Depends(get_db)) -> Alert:
    alert = get_alert_or_404(db, alert_id)

    min_price = payload.min_price if 'min_price' in payload.model_fields_set else alert.min_price
    max_price = payload.max_price if 'max_price' in payload.model_fields_set else alert.max_price
    validate_alert_bounds(min_price, max_price)

    if 'min_price' in payload.model_fields_set:
        alert.min_price = payload.min_price
    if 'max_price' in payload.model_fields_set:
        alert.max_price = payload.max_price
    if 'active' in payload.model_fields_set:
        alert.active = payload.active

    alert.current_state = AlertState.NORMAL

    db.commit()
    db.refresh(alert)
    return alert


@app.delete('/alerts/{alert_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(alert_id: int, db: Session = Depends(get_db)) -> Response:
    alert = get_alert_or_404(db, alert_id)
    db.delete(alert)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
