from fastapi import FastAPI
from redis_cli import RedisClient
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
app.logger = logger


redis_client = RedisClient()

app.logger.add("webservice.log", retention="10 days", backtrace=True, diagnose=True)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # TODO don't allow all origin
    allow_methods=["*"],
    allow_headers=["*"],
)
