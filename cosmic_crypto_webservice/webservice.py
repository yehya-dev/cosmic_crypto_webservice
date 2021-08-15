from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from pydantic import BaseModel, validator
from decimal import Decimal
from redis import Redis

from cosmic_crypto_webservice.message import TSLHandle

from loguru import logger

logger.add("webservice.log", retention="10 days", backtrace=True, diagnose=True)


app = FastAPI()
app.logger = logger
tsl_handle_client = TSLHandle()
redis_cli = Redis()


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TSLData(BaseModel):
    # TODO Provide more information i.e examples
    # TODO Improve type checking and validation
    # allowed Symbols, Follow percentages, amounts, api_key validation
    symbol: str
    follow_percentage: Decimal
    amount: Decimal
    cc_api_key: str

    @validator("cc_api_key", pre=True)
    def api_key_should_be_valid(cls, api_key):
        if not redis_cli.sismember("api_keys", api_key):
            raise ValueError("Invalid Api Key")
        return api_key


class BinanceData(BaseModel):

    binance_api_key: str
    binance_api_secret: str
    cc_api_key: str


@app.post("/add_tsl")
def trailing_stoploss(tsl_data: TSLData):
    tsl_handle_client.add_tsl(
        symbol=tsl_data.symbol,
        follow_percentage=tsl_data.follow_percentage,
        amount=tsl_data.amount,
        cc_api_key=tsl_data.cc_api_key,
    )
    logger.info(f"TSL added by {tsl_data.cc_api_key} for {tsl_data.symbol}")
    return {"status": "OK"}


@app.post("/set_binance_keys")
def set_binance_keys(binance_data: BinanceData):
    logger.info(f"Binance key set by {binance_data.cc_api_key}")
    return binance_data


# TODO : Set api key validation
# - All data on redis
