"""Interface Streamlit (optionnelle) de l'assistant de tests unitaires."""
import json
import os

import requests
import streamlit as st

AUTH_URL = os.getenv("AUTH_URL", "http://localhost:8001")
API_URL = os.getenv("API_URL", "http://localhost:8000")
TIMEOUT = 120

st.set_page_config(page_title="Assistant Tests Unitaires", page_icon="🧪", layout="wide")


def _error(resp: requests.Response) -> None:
    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        detail = resp.text
    st.error(f"Erreur {resp.status_code} : {detail}")


def call_api(method: str, path: str, payload: dict | None = None):
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        resp = requests.request(method, f"{API_URL}{path}", json=payload,
                                headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        st.error(f"API injoignable : {exc}")
        return None
    if resp.status_code != 200:
        _error(resp)
        return None
    return resp.json()


# ---------- Authentification ----------

if "token" not in st.session_state:
    st.session_state.token = None
    st.session_state.username = None

with st.sidebar:
    st.header("Compte")
    if st.session_state.token:
        st.success(f"Connecté : {st.session_state.username}")
        if st.button("Se déconnecter"):
            st.session_state.token = None
            st.session_state.username = None
            st.rerun()
    else:
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        col1, col2 = st.columns(2)
        creds = {"username": username, "password": password}
        if col1.button("Inscription", use_container_width=True):
            resp = requests.post(f"{AUTH_URL}/signup", json=creds, timeout=10)
            if resp.ok:
                st.success("Compte créé, connecte-toi.")
            else:
                _error(resp)
        if col2.button("Connexion", use_container_width=True):
            resp = requests.post(f"{AUTH_URL}/login", json=creds, timeout=10)
            if resp.ok:
                st.session_state.token = resp.json()["access_token"]
                st.session_state.username = username
                st.rerun()
            else:
                _error(resp)

st.title("🧪 Assistant de tests unitaires Python")

if not st.session_state.token:
    st.info("Connecte-toi dans la barre latérale pour utiliser l'assistant.")
    st.stop()

tabs = st.tabs(["Analyse", "Génération de test", "Explication", "Pipeline complet", "Chat", "Historique"])

with tabs[0]:
    code = st.text_area("Code Python", height=200, key="analyze_code")
    if st.button("Analyser", key="btn_analyze") and code:
        with st.spinner("Analyse en cours..."):
            result = call_api("POST", "/analyze", {"code": code})
        if result:
            if result["is_optimal"]:
                st.success("Code optimal")
            else:
                st.warning("Code non optimal")
            st.markdown("**Problèmes**")
            st.write(result["issues"] or "Aucun")
            st.markdown("**Suggestions**")
            st.write(result["suggestions"] or "Aucune")

with tabs[1]:
    code = st.text_area("Fonction Python", height=200, key="gen_code")
    if st.button("Générer le test", key="btn_gen") and code:
        with st.spinner("Génération en cours..."):
            result = call_api("POST", "/generate_test", {"code": code})
        if result:
            st.code(result["unit_test"], language="python")

with tabs[2]:
    unit_test = st.text_area("Test unitaire", height=200, key="explain_code")
    if st.button("Expliquer", key="btn_explain") and unit_test:
        with st.spinner("Explication en cours..."):
            result = call_api("POST", "/explain_test", {"unit_test": unit_test})
        if result:
            st.markdown(result["explanation"])

with tabs[3]:
    code = st.text_area("Code Python", height=200, key="pipeline_code")
    if st.button("Lancer le pipeline", key="btn_pipeline") and code:
        with st.spinner("Pipeline en cours..."):
            result = call_api("POST", "/full_pipeline", {"code": code})
        if result:
            st.subheader("1. Analyse")
            st.json(result["analysis"])
            if "error" in result:
                st.warning(f"Pipeline arrêté : {result['error']}")
            else:
                st.subheader("2. Test généré")
                st.code(result["test"]["unit_test"], language="python")
                st.subheader("3. Explication")
                st.markdown(result["explanation"]["explanation"])

with tabs[4]:
    message = st.chat_input("Ton message")
    if message:
        with st.spinner("..."):
            call_api("POST", "/chat", {"input": message})
    data = call_api("GET", "/history")
    for entry in (data or {}).get("history", []):
        if entry.get("endpoint") == "/chat":
            st.chat_message(entry["role"]).write(entry["content"])

with tabs[5]:
    if st.button("Rafraîchir", key="btn_history"):
        st.rerun()
    data = call_api("GET", "/history")
    if data:
        st.caption(f"{len(data['history'])} entrées")
        for entry in reversed(data["history"]):
            label = f"{entry['timestamp'][:19]} · {entry['endpoint']} · {entry['role']}"
            with st.expander(label):
                content = entry["content"]
                if isinstance(content, (dict, list)):
                    st.json(content)
                else:
                    if entry["role"] == "user":
                        st.code(content)
                    else:
                        st.markdown(content)
