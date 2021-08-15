from redis import Redis

api_key = "d8817d86-1e82-433f-88ce-b22f81255d14"
client = Redis()
client.flushdb()
print(api_key)
with client.pipeline() as pipe:
    pipe.sadd("api_keys", api_key)
    pipe.hset(
        api_key,
        mapping={"binance_api_key": "will fail", "binance_api_secret": "will fail"},
    )
    pipe.execute()
