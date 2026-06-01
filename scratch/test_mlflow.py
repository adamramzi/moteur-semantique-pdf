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
    return np.zeros((len(texts), 768), dtype=np.float32)

vectoriser._embed_batch = mock_embed_batch

# Import the app
from api.index import app
from database import get_user_id, sauvegarder_document, sauvegarder_index_db

client = TestClient(app)

def test_mlflow_tracking():
    print("--- DÉBUT DE LA VÉRIFICATION MLFLOW ---")
    
    # 1. Authentification
    from api.index import create_token
    email = "test@exemple.com"
    token = create_token(email)
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Récupérer l'ID utilisateur et pré-remplir l'index de test
    user_id = get_user_id(email)
    if not user_id:
        from database import creer_utilisateur_verifie, hacher_mot_de_passe
        creer_utilisateur_verifie(email, hacher_mot_de_passe("monMotDePasse123"), "127.0.0.1")
        user_id = get_user_id(email)
        
    print(f"Utilisateur de test chargé : {email} (ID: {user_id})")
    
    vecteurs = np.zeros((1, 768), dtype=np.float32)
    chunks = [{
        "texte": "StudySearch a été créé par Adam Ramzi en 2026. C'est un moteur de recherche sémantique de pointe pour analyser les documents PDF.", 
        "page": 1, 
        "fichier": "test_memo.txt"
    }]
    
    sauvegarder_document(user_id, "test_memo.txt", 1, type_fichier="TXT")
    sauvegarder_index_db(user_id, vecteurs, chunks)
    
    # 3. Envoyer une question au chat endpoint
    payload = {
        "query": "Qui a créé StudySearch ?",
        "mode": "resume",
        "pdf_name": "test_memo.txt",
        "history": []
    }
    
    print("\nEnvoi de la requête de chat...")
    res = client.post("/api/chat", headers=headers, json=payload)
    print("Statut réponse:", res.status_code)
    response_data = res.json()
    print("Réponse:", response_data)
    
    # 4. Vérifier localement si MLflow a créé l'historique de run
    print("\nInspection des répertoires MLflow...")
    mlruns_path = "./mlruns"
    if os.path.exists(mlruns_path):
        print("[OK] Dossier 'mlruns' détecté !")
        
        # Parcourir les runs enregistrés sous le premier exp (généralement '0')
        import mlflow
        client_mlflow = mlflow.tracking.MlflowClient()
        experiments = client_mlflow.search_experiments()
        
        for exp in experiments:
            print(f"Expérimentation : {exp.name} (ID: {exp.experiment_id})")
            runs = client_mlflow.search_runs(experiment_ids=[exp.experiment_id])
            print(f"Nombre de runs trouvés : {len(runs)}")
            
            if runs:
                latest_run = runs[0]
                print(f"\nDernier Run ID : {latest_run.info.run_id}")
                print("  Paramètres loggés :", latest_run.data.params)
                print("  Métriques loggées :", latest_run.data.metrics)
                
                # Vérifier la présence des artefacts
                artifacts = client_mlflow.list_artifacts(latest_run.info.run_id)
                artifact_paths = [art.path for art in artifacts]
                print("  Artefacts trouvés :", artifact_paths)
                
                # Assertions basiques pour confirmer que tout a fonctionné
                assert "model_name" in latest_run.data.params, "Paramètre 'model_name' manquant"
                assert "embedding_model" in latest_run.data.params, "Paramètre 'embedding_model' manquant"
                assert "vector_search_latency" in latest_run.data.metrics, "Métrique 'vector_search_latency' manquante"
                assert "llm_generation_latency" in latest_run.data.metrics, "Métrique 'llm_generation_latency' manquante"
                assert "prompt.txt" in artifact_paths, "Artefact 'prompt.txt' manquant"
                assert "response.txt" in artifact_paths, "Artefact 'response.txt' manquant"
                
                print("\nSUCCESS: TOUTES LES VÉRIFICATIONS MLFLOW SONT COMPLÈTES ET VALIDES !")
                return
    else:
        print("[ERROR] Dossier 'mlruns' introuvable ! MLflow n'a pas loggé le run.")
        sys.exit(1)

if __name__ == "__main__":
    test_mlflow_tracking()
