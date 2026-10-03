# Makefile

.PHONY: up down build rebuild logs ps test tests requirements clean

# `make` seul = build + démarrage de auth, main et streamlit
up:
	docker compose up -d --build auth main streamlit
	@echo "Auth      : http://localhost:8001/docs"
	@echo "Assistant : http://localhost:8000/docs"
	@echo "Streamlit : http://localhost:8501"

down:
	docker compose down

build:
	docker compose build

rebuild:
	docker compose down
	docker compose build
	docker compose up -d auth main streamlit

logs:
	docker compose logs -f --tail=50

ps:
	docker compose ps

# Tests pytest (unitaires + intégration conteneurs) dans le conteneur de test
tests:
	docker compose up -d --build auth main
	docker compose run --rm --build tests
	docker compose stop auth main



# Regenerate each service requirements.txt from pyproject.toml (uv.lock versions)
requirements:
	uv lock
	uv export --frozen --no-default-groups --group auth --no-hashes --no-emit-project -o src/api/authentification/requirements.txt
	uv export --frozen --no-default-groups --group assistant --no-hashes --no-emit-project -o src/api/assistant/requirements.txt
	uv export --frozen --no-default-groups --group streamlit --no-hashes --no-emit-project -o src/requirements.txt

clean:
	docker compose down --rmi local --volumes --remove-orphans
