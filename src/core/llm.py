"""Configuration et initialisation du modèle de langage."""
import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()

DEFAULT_MODEL = "groq:openai/gpt-oss-120b"


@lru_cache(maxsize=1)
def get_llm():
    """Modèle principal, instancié à la première utilisation (pas à l'import).

    Les clés (GROQ_API_KEY, LANGSMITH_*) sont lues depuis l'environnement / .env.
    """
    return init_chat_model(os.getenv("CHAT_MODEL", DEFAULT_MODEL), temperature=0)
