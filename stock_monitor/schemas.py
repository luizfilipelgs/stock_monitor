from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import AlertState, TriggerType
from .utils import normalize_symbol, validate_threshold_price


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


class AlertBatchCreate(BaseModel):
    below: list[float] = Field(default_factory=list)
    above: list[float] = Field(default_factory=list)

    @field_validator('below', 'above')
    @classmethod
    def validate_threshold_list(cls, values: list[float]) -> list[float]:
        normalized_values = [validate_threshold_price(value) for value in values]
        if len(set(normalized_values)) != len(normalized_values):
            raise ValueError('Threshold values must not contain duplicates in the same list.')
        return normalized_values

    @model_validator(mode='after')
    def ensure_any_threshold(self) -> 'AlertBatchCreate':
        if not self.below and not self.above:
            raise ValueError('At least one threshold must be provided in below or above.')
        return self


class AlertUpdate(BaseModel):
    trigger_type: TriggerType | None = None
    target_price: float | None = Field(default=None, gt=0)
    active: bool | None = None

    @field_validator('target_price')
    @classmethod
    def validate_threshold(cls, value: float | None) -> float | None:
        if value is None:
            return value
        return validate_threshold_price(value)

    @model_validator(mode='after')
    def validate_payload(self) -> 'AlertUpdate':
        if not self.model_fields_set:
            raise ValueError('At least one field must be provided.')
        return self


class AlertRead(BaseModel):
    id: int
    stock_id: int
    trigger_type: TriggerType
    target_price: float
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
