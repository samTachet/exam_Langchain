# Assistant de Tests Unitaires Python

Assistant basé sur **LangChain** qui analyse du code Python, génère des tests unitaires
**pytest** et les explique de manière pédagogique. Exposé via deux APIs **FastAPI**
conteneurisées (+ interface **Streamlit** optionnelle), tracé avec **LangSmith**.

## Architecture

```
                 ┌────────────────────┐  GET /me (JWT)  ┌────────────────────┐
 streamlit ────▶ │ main (port 8000)   │ ──────────────▶ │ auth (port 8001)   │
 (port 8501)     │ API assistant      │                 │ signup/login/me    │
                 └─────────┬──────────┘                 └────────────────────┘
                           │ chaînes LangChain + agent avec mémoire
                           ▼
                     LLM (Groq) ──▶ traces LangSmith
```

| Fichier | Rôle |
|---|---|
| `src/core/llm.py` | Initialisation du modèle depuis `CHAT_MODEL` (lazy) |
| `src/core/schemas.py` | Schémas Pydantic : sorties structurées, requêtes, utilisateur |
| `src/prompts/prompts.py` | Prompts : analyse, génération, explication, chat |
| `src/core/chains.py` | `prompt \| llm.with_structured_output(..., method="json_schema")` + agent `create_agent` avec checkpointer |
| `src/memory/memory.py` | `InMemorySaver` (contexte du chat par `thread_id`) + historique par utilisateur |
| `src/api/authentification/auth.py` | API d'authentification (JWT) |
| `src/api/assistant/main.py` | API principale |
| `src/app.py` | Interface Streamlit |
| `tests/` | Tests unitaires et d'intégration (pytest) |

Les modules importent depuis `src/` (`from core.chains import ...`) : `src/` est sur le
`PYTHONPATH` dans les conteneurs et via `tests/conftest.py` pour pytest.

## Configuration du `.env`

Fichier `.env` à la racine (ignoré par git, jamais copié dans les images) :

```env
GROQ_API_KEY=<votre_cle_groq>
CHAT_MODEL=groq:openai/gpt-oss-120b

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<votre_cle_langsmith>
LANGSMITH_PROJECT=exam_langchain
# Uniquement si le compte LangSmith est en région UE :
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
```

Optionnel : `JWT_SECRET_KEY` (sinon une clé aléatoire est générée au démarrage du service auth).

## Commandes

```bash
make            # build + démarrage de auth, main et streamlit
make tests      # lance la suite pytest dans le conteneur de test
```

| Commande | Effet |
|---|---|
| `make` / `make up` | Build et démarrage de auth, main, streamlit |
| `make tests` | Démarre auth + main, exécute `pytest tests` dans le conteneur `tests` |
| `make down` | Arrêt des services |
| `make rebuild` | Arrêt, rebuild, redémarrage |
| `make logs` / `make ps` | Logs / état des conteneurs |
| `make requirements` | Régénère les `requirements.txt` depuis `pyproject.toml` |
| `make clean` | Supprime conteneurs et images locales |

## Services et ports

| Service | URL |
|---|---|
| API d'authentification | http://localhost:8001 (Swagger : `/docs`) |
| API principale | http://localhost:8000 (Swagger : `/docs`) |
| Streamlit | http://localhost:8501 |

## Endpoints

### Authentification (port 8001)

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| POST | `/signup` | `{username, password}` | `{username}` — 400 si déjà existant |
| POST | `/login` | `{username, password}` | `{access_token, token_type}` — 401 si invalide |
| GET | `/me` | — (Bearer) | `{username}` — 401 si token invalide/expiré |

### Assistant (port 8000) — en-tête `Authorization: Bearer <token>` requis

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| POST | `/analyze` | `{code}` | `{is_optimal, issues, suggestions}` |
| POST | `/generate_test` | `{code}` | `{unit_test}` |
| POST | `/explain_test` | `{unit_test}` | `{explanation}` |
| POST | `/full_pipeline` | `{code}` | non optimal : `{error: "Code non optimal", analysis}` ; sinon `{analysis, test, explanation}` |
| POST | `/chat` | `{input}` | `{response}` — mémoire par utilisateur |
| GET | `/history` | — | `{history: [{role, content, endpoint, timestamp}, ...]}` |

Tous les endpoints enregistrent l'entrée (`user`) et le résultat (`assistant`) dans
l'historique de l'utilisateur.

**Erreurs** : 401 (token absent/invalide), 422 (corps invalide), 502 (erreur ou sortie
non conforme du LLM), 503 (service d'authentification injoignable).

## Tester

### Suite pytest

```bash
make tests
```

- `tests/test_auth_api.py`, `tests/test_assistant_api.py` : tests unitaires (LLM et auth simulés) ;
- `tests/test_container_integration.py` : appels réels aux conteneurs (`RUN_CONTAINER_TESTS=true`).

### Manuellement (curl)

```bash
# Inscription
curl -X POST localhost:8001/signup -H 'Content-Type: application/json' \
     -d '{"username":"sam","password":"secret"}'

# Login
TOKEN=$(curl -s -X POST localhost:8001/login -H 'Content-Type: application/json' \
     -d '{"username":"sam","password":"secret"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
H="Authorization: Bearer $TOKEN"; J='Content-Type: application/json'

# Analyse / génération / explication
curl -X POST localhost:8000/analyze       -H "$H" -H "$J" -d '{"code":"def add(a, b):\n    return a + b"}'
curl -X POST localhost:8000/generate_test -H "$H" -H "$J" -d '{"code":"def add(a, b):\n    return a + b"}'
curl -X POST localhost:8000/explain_test  -H "$H" -H "$J" -d '{"unit_test":"def test_add():\n    assert add(1, 2) == 3"}'

# Pipeline complet (code non optimal -> arrêt après l'analyse)
curl -X POST localhost:8000/full_pipeline -H "$H" -H "$J" -d '{"code":"def avg(v):\n    return sum(v) / len(v)"}'

# Chat avec mémoire puis historique
curl -X POST localhost:8000/chat -H "$H" -H "$J" -d '{"input":"Je m'"'"'appelle Sam."}'
curl -X POST localhost:8000/chat -H "$H" -H "$J" -d '{"input":"Comment je m'"'"'appelle ?"}'
curl localhost:8000/history -H "$H"
```

Dans Swagger (`/docs`) : bouton **Authorize**, coller le token **seul** (sans `Bearer`).

### En local sans Docker

```bash
cd src
uvicorn api.authentification.auth:app --port 8001
uvicorn api.assistant.main:app --port 8000     # autre terminal
```

### Observabilité

Chaque appel apparaît dans LangSmith (projet `exam_langchain`) : prompt envoyé, réponse
du modèle, chaîne ou agent utilisé, erreurs éventuelles.

## Limites connues

- Utilisateurs, historiques et mémoire de chat sont **en mémoire** : perdus au redémarrage.
- La décision `is_optimal` dépend du LLM et peut varier sur du code limite.
