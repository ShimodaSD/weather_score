import hmac
import os
import secrets
import time
from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
SESSION_SECONDS = 86400
SESSION_COOKIE = "wind_score_session"

AUTH_USERNAME = os.getenv("API_AUTH_USERNAME")
AUTH_PASSWORD = os.getenv("API_AUTH_PASSWORD")
ACCESS_TOKEN = os.getenv("API_ACCESS_TOKEN")

router = APIRouter(tags=["Auth"])


def authenticate_user(username: str, password: str) -> bool:
    return username == AUTH_USERNAME and password == AUTH_PASSWORD


def valid_session(value: str | None) -> bool:
    """Check a signed cookie and its fixed one-day expiry."""
    if not value or not ACCESS_TOKEN:
        return False
    try:
        expires, nonce, signature = value.split(".")
        expiry = int(expires)
    except ValueError:
        return False
    if not nonce or not (time.time() < expiry <= time.time() + SESSION_SECONDS):
        return False
    payload = f"{expires}.{nonce}"
    expected = hmac.new(ACCESS_TOKEN.encode(), payload.encode(), sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


async def require_access_token(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> str:
    if not (ACCESS_TOKEN and token == ACCESS_TOKEN) and not valid_session(session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token or session or ""


@router.post("/token", summary="Issue an access token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    response: Response,
) -> dict[str, str | None]:
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not ACCESS_TOKEN:
        raise HTTPException(status_code=503, detail="Authentication is unavailable")
    payload = f"{int(time.time()) + SESSION_SECONDS}.{secrets.token_hex(16)}"
    signature = hmac.new(ACCESS_TOKEN.encode(), payload.encode(), sha256).hexdigest()
    response.set_cookie(
        SESSION_COOKIE,
        f"{payload}.{signature}",
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return {"access_token": ACCESS_TOKEN, "token_type": "bearer"}


@router.get("/session", summary="Check the browser session")
async def get_session(
    session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict[str, bool]:
    if not valid_session(session):
        raise HTTPException(status_code=401, detail="Session expired")
    return {"authenticated": True}


@router.post("/logout", status_code=204, summary="End the browser session")
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="strict")
