from config import app, redis_client
from _schema import TSLData, SpotSchema, SpotsViewSchema
from typing import List
from fastapi import Depends

from _security import User, get_current_active_user, get_current_admin_user
from _helper import execute_spots_for_enrolled_users


@app.post("/add_tsl")
def trailing_stoploss(
    tsl_data: TSLData, current_user: User = Depends(get_current_active_user)
):
    return {"status": "TSL service under maintanance"}
    # get username and feed it into add tsl
    tsl_handle_client.add_tsl(
        symbol=tsl_data.symbol,
        follow_percentage=tsl_data.follow_percentage,
        amount=tsl_data.amount,
        username=current_user.username,
    )
    app.logger.info(f"TSL added by {tsl_data.cc_api_key} for {tsl_data.symbol}")
    return {"status": "OK"}


@app.post("/__create_signals__")  # TODO remove from Docs in production
def create_signals(
    signal_data: List[SpotSchema], current_user: User = Depends(get_current_admin_user)
):  # Signal Exec
    res = execute_spots_for_enrolled_users(signal_data)
    app.logger.info(f"Signals Executed : {res}")
    for key, val in res.items():
        print(key, str(val))
    redis_client.create_signals_in_db(signal_data)
    return {"status": "OK"}


@app.post("/__update_signals__")  # TODO remove from Docs in production
def update_signals(
    signal_data: List[SpotSchema], current_user: User = Depends(get_current_admin_user)
):
    redis_client.update_signals_in_db(signal_data)
    return {"status": "OK"}


@app.post("/__remove_signals__")  # TODO remove from Docs in production
def remove_signals(
    signal_data: List[SpotSchema], current_user: User = Depends(get_current_admin_user)
):
    redis_client.remove_signals_in_db(signal_data)
    return {"status": "OK"}


@app.post("/get_active_signals", response_model=SpotsViewSchema)
def get_active_signals(current_user: User = Depends(get_current_active_user)):
    return redis_client.get_active_signals_in_db()


@app.get("/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


# TODO If binance_api_keys are not set, don't allow to use endpoints that required them (Depends can do the trick)


# TODO - exec signal when new signals are added for a set of users
# - Remove them when remove is triggered
# Validate the added binance keys

# TODO people shouldn't be able to make the username 'users' coz that would coz problems (error in redis)
