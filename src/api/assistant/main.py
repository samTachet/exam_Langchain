"""API principale de l'assistant de tests unitaires.

Identifie l'utilisateur via l'API d'authentification (GET {AUTH_URL}/me).
Lancement local (depuis src/) : uvicorn api.assistant.main:app --port 8000
"""
import logging
import os
from typing import Callable, TypeVar

import requests
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from core.chains import (
    get_analysis_chain,
    get_chat_agent,
    get_explain_test_chain,
    get_test_chain,
)
from core.schemas import ChatRequest, CodeRequest, TestRequest, User
from memory.memory import add_to_history, get_history, get_thread_config

AUTH_URL = os.getenv("AUTH_URL", "http://localhost:8001")

logger = logging.getLogger("assistant")
app = FastAPI(title="Assistant Tests Unitaires API", version="1.0")
bearer = HTTPBearer(auto_error=False)

T = TypeVar("T")


# ---------- Authentification (déléguée à l'API auth) ----------

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token manquant.")
    try:
        resp = requests.get(
            f"{AUTH_URL}/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
            timeout=5,
        )
    except requests.RequestException as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Service d'authentification injoignable.") from exc
    if resp.status_code == 401:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré.")
    if resp.status_code != 200:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            detail="Réponse inattendue du service d'authentification.")
    return User(**resp.json())


# ---------- Appel LLM avec conversion des erreurs en réponses HTTP ----------

def _call_llm(fn: Callable[[], T]) -> T:
    try:
        return fn()
    except HTTPException:
        raise
    except ValidationError as exc:
        logger.exception("Sortie LLM non conforme au schéma")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            detail="La réponse du modèle ne respecte pas le format attendu.") from exc
    except Exception as exc:  # quota, réseau, clé invalide...
        logger.exception("Erreur lors de l'appel au LLM")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            detail=f"Erreur du modèle de langage : {type(exc).__name__}") from exc


def _analyze(code: str):
    return _call_llm(lambda: get_analysis_chain().invoke({"code": code}))


def _generate(code: str):
    return _call_llm(lambda: get_test_chain().invoke({"code": code}))


def _explain(unit_test: str):
    return _call_llm(lambda: get_explain_test_chain().invoke({"unit_test": unit_test}))


# ---------- Endpoints ----------
# Routes en `def` : les appels LLM sont bloquants, FastAPI les exécute en threadpool.

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: CodeRequest, user: User = Depends(get_current_user)):
    result = _analyze(req.code).model_dump()
    add_to_history(user.username, "user", req.code, "/analyze")
    add_to_history(user.username, "assistant", result, "/analyze")
    return result


@app.post("/generate_test")
def generate_test(req: CodeRequest, user: User = Depends(get_current_user)):
    result = _generate(req.code).model_dump()
    add_to_history(user.username, "user", req.code, "/generate_test")
    add_to_history(user.username, "assistant", result, "/generate_test")
    return result


@app.post("/explain_test")
def explain_test(req: TestRequest, user: User = Depends(get_current_user)):
    result = _explain(req.unit_test).model_dump()
    add_to_history(user.username, "user", req.unit_test, "/explain_test")
    add_to_history(user.username, "assistant", result, "/explain_test")
    return result


@app.post("/full_pipeline")
def full_pipeline(req: CodeRequest, user: User = Depends(get_current_user)):
    analysis = _analyze(req.code)
    if not analysis.is_optimal:
        response = {"error": "Code non optimal", "analysis": analysis.model_dump()}
    else:
        test = _generate(req.code)
        explanation = _explain(test.unit_test)
        response = {
            "analysis": analysis.model_dump(),
            "test": test.model_dump(),
            "explanation": explanation.model_dump(),
        }
    add_to_history(user.username, "user", req.code, "/full_pipeline")
    add_to_history(user.username, "assistant", response, "/full_pipeline")
    return response


@app.post("/chat")
def chat(req: ChatRequest, user: User = Depends(get_current_user)):
    result = _call_llm(lambda: get_chat_agent().invoke(
        {"messages": [{"role": "user", "content": req.input}]},
        config=get_thread_config(user.username),
    ))
    answer = result["messages"][-1].content
    add_to_history(user.username, "user", req.input, "/chat")
    add_to_history(user.username, "assistant", answer, "/chat")
    return {"response": answer}


@app.get("/history")
def history(user: User = Depends(get_current_user)):
    return {"history": get_history(user.username)}
