from fastapi import FastAPI
from pydantic import BaseModel
from decimal import Decimal

from cosmic_crypto_webservice.message import TSLHandle


app = FastAPI()
tsl_handle_client = TSLHandle()

class TSLData(BaseModel):
    #TODO Provide more information i.e examples
    #TODO Improve type checking and validation
    # allowed Symbols, Follow percentages, amounts, api_key validation
    symbol: str
    follow_percentage: Decimal
    amount: Decimal
    api_key: str


@app.post("/")
def trailing_stoploss(tsl_data: TSLData):
    tsl_handle_client.add_tsl(
        symbol=tsl_data.symbol,
        follow_percentage=tsl_data.follow_percentage,
        amount=tsl_data.amount
    )
    return tsl_data