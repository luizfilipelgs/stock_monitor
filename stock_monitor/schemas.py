from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import AlertState, TriggerType
from .utils import normalize_symbol, validate_alert_bounds


class StockCreate(BaseModel):
    symbol: str
    active: bool = True

    @field_validator('symbol')
    @classmethod
    def normalize_stock_symbol(cls, value: str) -> str:
        return normalize_symbol(value)


class StockUpdate(BaseModel):
    symbol: str | None = None
    active: bool | None = None

    @field_validator('symbol')
    @classmethod
    def normalize_stock_symbol(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return normalize_symbol(value)

    @model_validator(mode='after')
    def ensure_payload_has_updates(self) -> 'StockUpdate':
        if not self.model_fields_set:
            raise ValueError('At least one field must be provided.')
        return self


class AlertCreate(BaseModel):
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    active: bool = True

    @model_validator(mode='after')
    def validate_bounds(self) -> 'AlertCreate':
        validate_alert_bounds(self.min_price, self.max_price)
        return self


class AlertUpdate(BaseModel):
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    active: bool | None = None

    @model_validator(mode='after')
    def validate_payload(self) -> 'AlertUpdate':
        if not self.model_fields_set:
            raise ValueError('At least one field must be provided.')
        if 'min_price' in self.model_fields_set and 'max_price' in self.model_fields_set:
            validate_alert_bounds(self.min_price, self.max_price)
        return self


class AlertRead(BaseModel):
    id: int
    stock_id: int
    min_price: float | None
    max_price: float | None
    active: bool
    current_state: AlertState
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockRead(BaseModel):
    id: int
    symbol: str
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockDetailRead(StockRead):
    alerts: list[AlertRead]

    model_config = ConfigDict(from_attributes=True)


class StockPriceRead(BaseModel):
    id: int
    stock_id: int
    price: float
    collected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TriggeredAlertRead(BaseModel):
    id: int
    alert_id: int
    stock_id: int
    price: float
    trigger_type: TriggerType
    message: str
    triggered_at: datetime

    model_config = ConfigDict(from_attributes=True)
