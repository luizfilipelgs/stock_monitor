from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AlertState(str, Enum):
    NORMAL = 'NORMAL'
    BELOW = 'BELOW'
    ABOVE = 'ABOVE'


class TriggerType(str, Enum):
    BELOW = 'BELOW'
    ABOVE = 'ABOVE'


class Stock(Base):
    __tablename__ = 'stocks'

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    alerts: Mapped[list['Alert']] = relationship(
        back_populates='stock',
        cascade='all, delete-orphan',
        order_by='Alert.id',
    )
    prices: Mapped[list['StockPrice']] = relationship(
        back_populates='stock',
        cascade='all, delete-orphan',
        order_by='StockPrice.id',
    )
    triggered_alerts: Mapped[list['TriggeredAlert']] = relationship(
        back_populates='stock',
        cascade='all, delete-orphan',
        order_by='TriggeredAlert.id',
    )


class Alert(Base):
    __tablename__ = 'alerts'

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey('stocks.id', ondelete='CASCADE'), index=True)
    trigger_type: Mapped[TriggerType] = mapped_column(SqlEnum(TriggerType, native_enum=False), nullable=False)
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    current_state: Mapped[AlertState] = mapped_column(
        SqlEnum(AlertState, native_enum=False),
        default=AlertState.NORMAL,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    stock: Mapped[Stock] = relationship(back_populates='alerts')
    triggered_alerts: Mapped[list['TriggeredAlert']] = relationship(
        back_populates='alert',
        cascade='all, delete-orphan',
        order_by='TriggeredAlert.id',
    )


class StockPrice(Base):
    __tablename__ = 'stock_prices'

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey('stocks.id', ondelete='CASCADE'), index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    stock: Mapped[Stock] = relationship(back_populates='prices')


class TriggeredAlert(Base):
    __tablename__ = 'triggered_alerts'

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey('alerts.id', ondelete='CASCADE'), index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey('stocks.id', ondelete='CASCADE'), index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    trigger_type: Mapped[TriggerType] = mapped_column(SqlEnum(TriggerType, native_enum=False), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    alert: Mapped[Alert] = relationship(back_populates='triggered_alerts')
    stock: Mapped[Stock] = relationship(back_populates='triggered_alerts')
