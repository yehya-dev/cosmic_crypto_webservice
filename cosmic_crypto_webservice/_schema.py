from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List
from datetime import datetime


class TSLData(BaseModel):
    # TODO Provide more information i.e examples
    # TODO Improve type checking and validation
    # allowed Symbols, Follow percentages, amounts, api_key validation
    symbol: str
    follow_percentage: Decimal
    amount: Decimal


class SpotSchema(BaseModel):
    spot_id: str
    buy_price: Decimal
    chart_url: Optional[str]
    created_at: datetime
    current_price: Optional[Decimal]
    risk: str
    pair: str
    stop_price: Decimal
    symbol: str
    tp1: Decimal
    tp2: Decimal
    tp3: Decimal
    tp_done: int
    total_tp: int
    spot_type: str
    coin_logo_url: str

    def redis_serializable_dict(self):
        new_dict = {}
        for key, value in self.dict().items():
            if isinstance(value, Decimal):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.strftime("%Y-%m-%dT%H:%M:%S")
            new_dict[key] = value
        return new_dict


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    is_admin: Optional[bool] = False
    disabled: Optional[bool] = None
    binance_api_key: Optional[str]
    binance_api_secret: Optional[str]


class UserInDB(User):
    password: str


class SpotsViewSchema(BaseModel):
    __root__: List[SpotSchema]
