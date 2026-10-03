"""API d'authentification : inscription, connexion (JWT), utilisateur courant.

Base utilisateurs simulée en mémoire (`fake_users_db`), perdue au redémarrage.
Lancement local (depuis src/) : uvicorn api.authentification.auth:app --port 8001
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.schemas import User, UserCredentials

# Sans JWT_SECRET_KEY, une clé aléatoire est générée au démarrage (tokens invalidés au redémarrage).
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

app = FastAPI(title="Auth API", version="1.0")
bearer = HTTPBearer(auto_error=False)

# username -> {"username", "salt", "hashed_password"}
fake_users_db: dict[str, dict[str, str]] = {}


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()


def _create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise unauthorized
    username = payload.get("sub")
    if username is None or username not in fake_users_db:
        raise unauthorized
    return User(username=username)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/signup")
def signup(creds: UserCredentials):
    if creds.username in fake_users_db:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Ce nom d'utilisateur existe déjà.")
    salt = secrets.token_hex(16)
    fake_users_db[creds.username] = {
        "username": creds.username,
        "salt": salt,
        "hashed_password": _hash_password(creds.password, salt),
    }
    return {"username": creds.username}


@app.post("/login")
def login(creds: UserCredentials):
    user = fake_users_db.get(creds.username)
    if user is None or not hmac.compare_digest(
        user["hashed_password"], _hash_password(creds.password, user["salt"])
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides.")
    return {"access_token": _create_access_token(creds.username), "token_type": "bearer"}


@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return user.model_dump()
