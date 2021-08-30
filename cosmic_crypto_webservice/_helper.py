from typing import List, Dict
from _schema import SpotSchema, User
from binance import Client
from binance.helpers import round_step_size
from binance.enums import SIDE_SELL, TIME_IN_FORCE_GTC
from binance.exceptions import BinanceAPIException
from decimal import Decimal
from _exceptions import (
    PriceOutOfRange,
    UnrecognizedQuote,
    NotEnoughQuoteBalance,
    QuoteAmountTooLow,
    OrderFailed,
    NotEnoughPerms,
)
from config import redis_client


def execute_spots_for_enrolled_users(spots: List[SpotSchema]) -> dict:
    """Executes a list of spots for enrolled users
    Args:
        spots (List[SpotSchema]): list of spot signals
    """
    enrolled_users = redis_client.get_auto_exec_enrolled_users()
    users_result = dict()
    for user in enrolled_users:
        try:
            user_exec_result = execute_spots(spots, user)
        except (NotEnoughPerms, Exception) as e:
            users_result[user.username] = {"status": False, "result": e}
        else:
            users_result[user.username] = {"status": True, "result": user_exec_result}
    return users_result


def execute_spots(
    spots: List[SpotSchema],
    user_data: User,
    amount_of_quote_to_buy_with: Decimal = Decimal("11"),
):
    """Execute multiple spot signals

    Args:
        spots (List[SpotSchema]): List of spots signal data
        user_data (User): Details of the user
    Raises:
        NotEnoughPerms: Spot Trading Perms are not allowed for the api
    Returns:
        [dict]: Result of each of the signal execution by their id as the key
    """
    binance_client = Client(user_data.binance_api_key, user_data.binance_api_secret)
    perms = binance_client._request_margin_api(
        "get", "account/apiRestrictions", True, data={}
    )
    if not perms["enableSpotAndMarginTrading"]:
        raise NotEnoughPerms("Spot Trading Perms are not allowed for the api")

    exec_result = dict()
    for spot in spots:
        try:
            res = execute_spot(spot, binance_client, amount_of_quote_to_buy_with)
            exec_result[spot.spot_id] = {"status": True, "result": res}
        except (
            PriceOutOfRange,
            UnrecognizedQuote,
            NotEnoughQuoteBalance,
            QuoteAmountTooLow,
            OrderFailed,
            Exception,  # < ------ Hem ? Required on product to not cause problems for all users because of single user
        ) as e:
            # TODO log
            exec_result[spot.spot_id] = {"status": False, "result": e}

    return exec_result


def execute_spot(
    spot: SpotSchema,
    binance_client: Client,
    amount_of_quote_to_buy_with: Decimal = Decimal(
        "11.0"
    ),  # Minimum 10 USDT for X/USDT (Approx, might go a bit above)
    max_percent_above_buy_price=Decimal("0.5"),  # Between 0 - 1
) -> Dict[str, dict]:
    """Exeute a spot signal with a market buy order and a OCO sell order depending to spot data passed

    Args:
        spot (SpotSchema): The signal spot data
        binance_client (Client): binance client object of the user
        amount_of_quote_to_buy_with (Decimal, optional): amount of quote to be used in exceuting the signal. Defaults to Decimal( "10.0" ).

    Raises:
        OrderFailed: Order couldn't be completed
        PriceOutOfRange: Current price of the asset is not in a range that the signal can be safely executed

    Returns:
        [Dict[str, dict]]: buy_order details and sell_order details by the respective names
    """
    current_symbol_price = binance_client.get_symbol_ticker(symbol=spot.pair.upper())[
        "price"
    ]
    current_symbol_price = Decimal(current_symbol_price)

    highest_acceptable_price = spot.buy_price + (
        max_percent_above_buy_price * (spot.tp1 - spot.buy_price)
    )

    if highest_acceptable_price > current_symbol_price > spot.stop_price:
        amount_of_base_asset_to_buy = get_amount_of_base_asset(
            binance_client=binance_client,
            spot=spot,
            amount_of_quote_to_buy_with=amount_of_quote_to_buy_with,
            price_of_base=current_symbol_price,
        )
        try:
            params = {
                "symbol": spot.pair.upper(),
                "quantity": str(amount_of_base_asset_to_buy),
            }
            buy_order = binance_client.order_market_buy(**params)
        except BinanceAPIException as e:
            raise OrderFailed(
                f"Buy Order Failed, Server Responded With {e.message}", params=params
            )
        else:
            try:
                params = {
                    "symbol": spot.pair.upper(),
                    "side": SIDE_SELL,
                    "quantity": str(amount_of_base_asset_to_buy),
                    "stopPrice": str(spot.stop_price),
                    "stopLimitPrice": str(spot.stop_price),
                    "stopLimitTimeInForce": TIME_IN_FORCE_GTC,
                    "price": str(spot.tp1),
                }
                sell_order = binance_client.create_oco_order(**params)
                return {"buy": buy_order, "sell": sell_order}
            except BinanceAPIException as e:
                raise OrderFailed(
                    f"Sell (OCO) Order Failed, Server Responded With {e.message}",
                    params=params,
                )
    else:
        raise PriceOutOfRange(
            f"Current Price - {current_symbol_price}, Lower_Bound - {spot.stop_price}, Upper_Bound - {highest_acceptable_price}"
        )


def get_pair_info(client: Client, pair: str):
    """Get the minimum allowed base amount and quote amount

    Args:
        client (Client): Binance Client of the user
        pair ([type]):

    Returns:
        [str]: pair the info is required for
    """
    info = client.get_symbol_info(pair)
    step_size = None
    minimum_amount_of_quote_required = None
    for item in info["filters"]:
        if item["filterType"] == "LOT_SIZE":
            step_size = Decimal(item["stepSize"])
        elif item["filterType"] == "MIN_NOTIONAL":
            minimum_amount_of_quote_required = item["minNotional"]
        if step_size and minimum_amount_of_quote_required:
            return Decimal(step_size), Decimal(
                minimum_amount_of_quote_required
            ) + Decimal(
                "1"
            )  # 11 is the minimum required quote for X/USDT
            # It's actually 10.something, but it's hard to do the perfect value. so 11. (perfect value keeps changing as the price keeps changing


def get_amount_of_base_asset(
    binance_client: Client,
    spot: SpotSchema,
    amount_of_quote_to_buy_with: Decimal,
    price_of_base: Decimal,
):
    """Get the amount of base asset that can be bought with a specific amount of quote,
        Also checks the balance and the validity of the pair

    Args:
        binance_client (Client): Binance client object for a user
        spot (SpotSchema): The Signal Data
        amount_of_quote_to_buy_with (Decimal): Amount of quote that you are planning to buy with
        price_of_base (Decimal): Current price of the base asset

    Raises:
        QuoteAmountTooLow: If the quote specified is lower than the minimum
        UnrecognizedQuote: Invalid Pair
        NotEnoughQuoteBalance: Account doesn't have the speicfied amount of quote

    Returns:
        [Decimal]: The amount of base than can be bought
    """
    step_size, minimum_amount_of_quote_required = get_pair_info(
        binance_client, spot.pair
    )
    if amount_of_quote_to_buy_with < minimum_amount_of_quote_required:
        raise QuoteAmountTooLow(
            f"Aleast {minimum_amount_of_quote_required} of quote is required",
            params={
                "amount_of_quote_to_buy_with": amount_of_quote_to_buy_with,
                "minimum_amount_of_quote_required": minimum_amount_of_quote_required,
            },
        )
    quote = spot.pair.split(spot.symbol)[1]
    quote_balance = binance_client.get_asset_balance(asset=quote)

    if quote_balance:
        quote_balance = Decimal(quote_balance["free"])
    else:
        raise UnrecognizedQuote(
            f"There was an error getting the quote balance for : {quote}",
            params={"quote": quote},
        )
    if quote_balance < amount_of_quote_to_buy_with:
        raise NotEnoughQuoteBalance(
            f"The specified amount of {quote} is not available",
            params={
                "quote_balance": quote_balance,
                "amount_of_quote_to_buy_with": amount_of_quote_to_buy_with,
            },
        )

    amount_i_can_buy = amount_of_quote_to_buy_with / price_of_base
    amount_i_can_buy = Decimal(
        str(round_step_size(quantity=amount_i_can_buy, step_size=step_size))
    )
    return amount_i_can_buy
