import redis
from decimal import Decimal

# change

class TSLHandle(redis.Redis):
    """
    ### Redis client with added methods
    DB Schema:
        - last_tsl_id = 11
        - 1: {id: 1, symbol: "BTCUSDT", follow_percentage: "2.2", amount: "43", cc_api_key: "Hkre2032i350dfddfsdsfa"}
        - 2: {id: 2, symbol: "RUNEUSDT", follow_percentage: "1.2", amount: "13" cc_api_key: "Hkre2032i350dfddfsdsfa"}
        - 3: {id: 3, symbol: "RUNEUSDT", follow_percentage: "4.1", amount: "31" cc_api_key: "Hkre2032i350dfddfsdsfa"}
        - "BTCUSDT" : {1} - These values represent the key for the hash
        - "RUNEUSDT": {2, 3} - same here
        - live_symbols : { "BTCUSDT", "RUNEUSDT" }
        - api_keys : { Hkre2032i350dfddfsdsfa, ...}
        - Hkre2032i350dfddfsdsfa: {binance_api_key: sdafasf3423434324324, binance_api_secret: saf23324sdfsfdasf}
    """

    def add_tsl(self,*,symbol : str, follow_percentage : Decimal, amount: Decimal, cc_api_key: str):
        """Adds the tsl data to the db"""
        # Increments last_tsl_id 
        # Creates hash with id as key
        # Stores id in a set with the key symbol , ex: BTCUSDT: {1, }

        last_tsl_id = self.get('last_tsl_id')
        if last_tsl_id:
            tsl_id = int(last_tsl_id) + 1
        else:
            tsl_id = 0

        with self.pipeline() as pipe:
            pipe.set('last_tsl_id', tsl_id)
            pipe.hmset(tsl_id, {
                'id': tsl_id,
                'symbol': symbol, #TODO Not really needed, remove after debug
                'follow_percentage': str(follow_percentage),
                'amount': str(amount),
                'cc_api_key': cc_api_key
            })
            pipe.sadd(symbol, tsl_id)
            pipe.sadd('live_symbols', symbol)
            pipe.execute()

