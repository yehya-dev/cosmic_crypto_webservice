import redis
from decimal import Decimal
from loguru import logger
from _schema import SpotSchema, SpotsViewSchema, User
from typing import List


class RedisClient(redis.Redis):
    def __init__(self):
        self.tsl_handle_client = redis.Redis(db=0, decode_responses=True)
        self.user_details_client = redis.Redis(db=1, decode_responses=True)
        self.signals_details_client = redis.Redis(db=2, decode_responses=True)
        self.exec_signals_client = redis.Redis(db=3, decode_responses=True)

    def add_tsl(
        self,
        *,
        symbol: str,
        follow_percentage: Decimal,
        amount: Decimal,
        username: str,
    ):
        """Adds a tsl into the redis_database

        Args:
            symbol (str): symbol to trade, ex: BTCUSDT
            follow_percentage (Decimal): at what percentage to follow the price at
            amount (Decimal): amount to sell when trigger price is reached
            cc_api_key (str): api_key of the user
        """
        # Increments last_tsl_id
        # Creates hash with id as key
        # Stores id in a set with the key symbol , ex: BTCUSDT: {1, }

        last_tsl_id = self.tsl_handle_client.get("last_tsl_id")
        if last_tsl_id:
            tsl_id = int(last_tsl_id) + 1
        else:
            tsl_id = 0

        with self.tsl_handle_client.pipeline() as pipe:
            pipe.set("last_tsl_id", tsl_id)
            pipe.hmset(
                tsl_id,
                {
                    "id": tsl_id,
                    "symbol": symbol,
                    "follow_percentage": str(follow_percentage),
                    "amount": str(amount),
                    "username": username,
                },
            )
            pipe.sadd(symbol, tsl_id)
            pipe.sadd("live_symbols", symbol)
            pipe.execute()
            logger.info(f"Added TSL : {tsl_id} to redis")

    def create_signals_in_db(self, signals: List[SpotSchema]):
        with self.signals_details_client.pipeline() as pipe:
            for item in signals:
                pipe.sadd("spots", item.spot_id)
                pipe.hmset(item.spot_id, item.redis_serializable_dict())
                pipe.execute()
                logger.info(f"Added Signal {item.spot_id} in db")

    def update_signals_in_db(self, signals: List[SpotSchema]):
        with self.signals_details_client.pipeline() as pipe:
            for item in signals:
                pipe.sadd("spots", item.spot_id)
                pipe.hmset(item.spot_id, item.redis_serializable_dict())
                pipe.execute()
                logger.info(f"Updated Signal {item.spot_id} in db")

    def remove_signals_in_db(self, signals: List[SpotSchema]):
        with self.signals_details_client.pipeline() as pipe:
            for item in signals:
                pipe.srem("spots", item.spot_id)
                pipe.delete(item.spot_id)
                pipe.execute()
                logger.info(f"Deleted Signal {item.spot_id} in db")

    def get_active_signals_in_db(self):
        spot_ids = self.signals_details_client.smembers("spots")
        return SpotsViewSchema.parse_obj(
            [self.signals_details_client.hgetall(spot_id) for spot_id in spot_ids]
        )

    def get_auto_exec_enrolled_users(self):
        enrolled_usernames = self.signals_details_client.smembers(
            "signal_execution_enrolled_users"
        )
        enrolled_users_list: List[User] = []
        for user in enrolled_usernames:
            user_data = self.user_details_client.hgetall(user)
            enrolled_users_list.append(User(**user_data))
        return enrolled_users_list

    def is_user_in_db(self, username):
        return self.user_details_client.sismember("users", username)

    def get_user_data(self, username):
        return self.user_details_client.hgetall(username)


# main keys : spots, live_symbols,
