"""Mémoire multi-utilisateurs, en mémoire tant que le service tourne.

- `checkpointer` (LangGraph) : contexte de conversation de l'agent de chat, par thread_id ;
- historique par utilisateur : tous les échanges, exposés par /history.
"""
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()

_history: dict[str, list[dict[str, Any]]] = {}
_lock = Lock()


def get_thread_id(username: str) -> str:
    """Identifiant de conversation unique par utilisateur."""
    return f"user-{username}"


def get_thread_config(username: str) -> dict:
    return {"configurable": {"thread_id": get_thread_id(username)}}


def add_to_history(username: str, role: str, content: Any, endpoint: str) -> None:
    entry = {
        "role": role,
        "content": content,
        "endpoint": endpoint,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        _history.setdefault(username, []).append(entry)


def get_history(username: str) -> list[dict[str, Any]]:
    with _lock:
        return list(_history.get(username, []))


def clear_history(username: str | None = None) -> None:
    """Vide l'historique d'un utilisateur, ou de tous si username est None."""
    with _lock:
        if username is None:
            _history.clear()
        else:
            _history.pop(username, None)
