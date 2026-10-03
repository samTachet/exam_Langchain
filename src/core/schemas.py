"""Schémas Pydantic : sorties structurées du LLM, requêtes API, utilisateur."""
from pydantic import BaseModel, Field


# ---------- Sorties structurées du LLM ----------
# Champs sans valeur par défaut : exigé par le mode json_schema strict.

class CodeAnalysisResult(BaseModel):
    """Analyse d'un extrait de code Python."""
    is_optimal: bool = Field(description="True si le code est correct et sans problème notable, False sinon.")
    issues: list[str] = Field(description="Problèmes identifiés (bugs, cas limites, performance, lisibilité). Vide si aucun.")
    suggestions: list[str] = Field(description="Améliorations concrètes proposées. Vide si aucune.")


class GeneratedTestResult(BaseModel):
    """Test unitaire pytest généré."""
    unit_test: str = Field(description="Code Python complet du test pytest, imports compris.")


class TestExplanationResult(BaseModel):
    """Explication pédagogique d'un test unitaire."""
    explanation: str = Field(description="Explication pédagogique et détaillée du test, pas à pas.")


# ---------- Requêtes API ----------

class CodeRequest(BaseModel):
    code: str = Field(min_length=1)


class TestRequest(BaseModel):
    unit_test: str = Field(min_length=1)


class ChatRequest(BaseModel):
    input: str = Field(min_length=1)


# ---------- Utilisateurs ----------

class User(BaseModel):
    username: str


class UserCredentials(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
