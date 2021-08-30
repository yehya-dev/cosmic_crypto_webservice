from pydantic import BaseModel
from typing import Optional, Type
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from config import app, redis_client, RedisClient
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from _schema import Token, TokenData, User, UserInDB


SECRET_KEY = "ba204f940bf22f69ac3a06a6da9b4eb944b77eefa68c2f9cfc1b7499d168e4e6"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080


oauth_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_user(
    redis_client: RedisClient, username: str, response_model: Type[BaseModel] = User
):
    if redis_client.is_user_in_db(username=username):
        user_dict = redis_client.get_user_data(username=username)
        return response_model(**user_dict)


def authenticate_user(redis_cli: RedisClient, username: str, password: str):
    user: UserInDB = get_user(redis_cli, username, response_model=UserInDB)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


async def get_current_user(token: str = Depends(oauth_scheme)):
    creditionals_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise creditionals_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise creditionals_exception
    user: User = get_user(
        redis_client, username=token_data.username, response_model=User
    )
    if user is None:
        raise creditionals_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(
            status_code=400,
            detail="Inactive user, Contact admin to reactivate your account",
        )
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=400, detail="You are not authorized to perform this action"
        )
    return current_user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(redis_client, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_admin:
        accesss_token_expires = timedelta(days=365)
    else:
        accesss_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    accesss_token = create_access_token(
        data={"sub": user.username}, expires_delta=accesss_token_expires
    )
    return {"access_token": accesss_token, "token_type": "bearer"}
