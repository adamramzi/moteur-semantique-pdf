import os
import sys
import numpy as np
from fastapi.testclient import TestClient

# Add workspace directory to path to import modules
sys.path.insert(0, r"c:\Users\dell\Desktop\moteur_semantique - Copie")

# Load environment variables
from dotenv import load_dotenv
load_dotenv(r"c:\Users\dell\Desktop\moteur_semantique - Copie\.env")

# Mock the Hugging Face embedding function to run without API token
import vectoriser
def mock_embed_batch(texts, batch_size=32):
    print(f"[MOCK] Vectorisation de {len(texts)} textes...")
    return np.zeros((len(texts), 384), dtype=np.float32)

vectoriser._embed_batch = mock_embed_batch

# Import the app
from api.index import app
from database import get_user_id, sauvegarder_document, sauvegarder_index_db

client = TestClient(app)

def test_history_parsing():
    print("--- DÉBUT DES TESTS DE LA MÉMOIRE CONVERSATIONNELLE ---")
    
    # 1. Authentification
    from api.index import create_token
    email = "test@exemple.com"
    token = create_token(email)
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Récupérer l'ID utilisateur
    user_id = get_user_id(email)
    if not user_id:
        # Créer l'utilisateur si absent
        from database import creer_utilisateur_verifie, hacher_mot_de_passe
        creer_utilisateur_verifie(email, hacher_mot_de_passe("monMotDePasse123"), "127.0.0.1")
        user_id = get_user_id(email)
        
    print(f"Utilisateur de test chargé : {email} (ID: {user_id})")
    
    # 3. Pré-remplir l'index directement dans la base de données pour bypasser Hugging Face
    print("Pré-population de l'index de test dans la base de données...")
    vecteurs = np.zeros((1, 384), dtype=np.float32)
    chunks = [{
        "texte": "StudySearch a été créé par Adam Ramzi en 2026. C'est un moteur de recherche sémantique de pointe pour analyser les documents PDF.", 
        "page": 1, 
        "fichier": "test_memo.txt"
    }]
    
    sauvegarder_document(user_id, "test_memo.txt", 1, type_fichier="TXT")
    sauvegarder_index_db(user_id, vecteurs, chunks)
    
    # 4. Vérifier les stats
    stats_res = client.get("/api/stats", headers=headers)
    print("Stats utilisateur:", stats_res.json())
    
    # 5. Envoyer une première question avec un historique vide
    payload_q1 = {
        "query": "Qui a créé StudySearch ?",
        "mode": "resume",
        "pdf_name": "test_memo.txt",
        "history": []
    }
    
    print("\n[Q1] Envoi de la première question...")
    res_q1 = client.post("/api/chat", headers=headers, json=payload_q1)
    print("Statut Q1:", res_q1.status_code)
    response_data1 = res_q1.json()
    print("Réponse Q1:", response_data1)
    
    reponse_groq1 = response_data1.get("reponse", "")
    
    # 6. Envoyer une deuxième question avec l'historique de la première
    # L'historique simule ce que fait le frontend au moment d'appeler l'API pour Q2.
    # chatHistory contient : [Q1, R1, Q2]
    history = [
        {"role": "user", "content": "Qui a créé StudySearch ?"},
        {"role": "bot", "content": reponse_groq1},
        {"role": "user", "content": "En quelle année l'a-t-il fait ?"}  # Q2
    ]
    
    payload_q2 = {
        "query": "En quelle année l'a-t-il fait ?",
        "mode": "resume",
        "pdf_name": "test_memo.txt",
        "history": history
    }
    
    print("\n[Q2] Envoi de la deuxième question dépendante du contexte (avec historique)...")
    res_q2 = client.post("/api/chat", headers=headers, json=payload_q2)
    print("Statut Q2:", res_q2.status_code)
    response_data2 = res_q2.json()
    print("Réponse Q2:", response_data2)
    
    print("\n--- FIN DES TESTS ---")

if __name__ == "__main__":
    test_history_parsing()
