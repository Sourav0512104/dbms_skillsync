import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from .db import pg_conn
from .models import UserSummary

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60
password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


def _secret_key() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters")
    return secret


def validate_auth_settings() -> None:
    _secret_key()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str | None) -> bool:
    return bool(stored_hash) and password_hash.verify(password, stored_hash)


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expires_at},
        _secret_key(),
        algorithm=ALGORITHM,
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> UserSummary:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = jwt.decode(
            credentials.credentials,
            _secret_key(),
            algorithms=[ALGORITHM],
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError, RuntimeError) as error:
        raise unauthorized from error

    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, full_name, email, availability_hours, experience_years
                FROM users
                WHERE user_id = %s
                """,
                (user_id,),
            )
            user = cur.fetchone()

    if user is None:
        raise unauthorized
    return UserSummary(**user)
