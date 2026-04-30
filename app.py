from tasks import get_stock_price

get_stock_price.delay('PETR4')

""" from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tasks import get_stock_price


app = FastAPI()


class StockPriceRequest(BaseModel):
    stock_name: str


@app.post("/stock_price")
def stock_price(data: StockPriceRequest):
    if not data.stock_name:
        raise HTTPException(
            status_code=400,
            detail="Nome da ação é necessário"
        )

    get_stock_price.delay(data.stock_name)

    return {"message": "Requisição processada com sucesso!"} """
