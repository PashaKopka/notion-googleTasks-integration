import datetime
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError, decode
from sqlalchemy.ext.asyncio import AsyncSession

from config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from models.models import User as UserDB
from models.models import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def generate_access_token(user: UserDB) -> str:
    payload = {
        "sub": user.email,
        "exp": datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, payload["exp"]


async def validate_token(
    token: str = Security(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[UserDB]:
    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        expiration = payload.get("exp")

        expiration_datetime = datetime.datetime.fromtimestamp(expiration)
        current_datetime = datetime.datetime.now(expiration_datetime.tzinfo)
        if email and expiration and current_datetime < expiration_datetime:
            user = await UserDB.get_by_email(email, db)
            if user:
                return user
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    raise HTTPException(status_code=401, detail="Invalid credentials")
