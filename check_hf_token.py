import os
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

token = os.getenv("HF_API_TOKEN", "")

print("=======================================================")
print(" diagnostic de votre token hugging face")
print("=======================================================")

if not token:
    print("[ERREUR] Aucun token trouvé dans votre fichier .env ou vos variables d'environnement !")
    print("Veuillez ajouter la ligne : HF_API_TOKEN=votre_token")
    exit(1)

print(f"Token trouvé : {token[:6]}...{token[-4:] if len(token) > 10 else ''}")
print(f"Longueur du token : {len(token)} caractères")

url = "https://api-inference.huggingface.co/models/sentence-transformers/all-mpnet-base-v2"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

try:
    res = requests.post(url, headers=headers, json={"inputs": ["Test"]}, timeout=15)
    print("\n[RÉSULTAT DE L'API HUGGING FACE]")
    print(f"Statut HTTP : {res.status_code}")
    
    if res.status_code == 200:
        print("[SUCCÈS] Votre token est parfaitement VALIDE et l'API répond correctement !")
        print("Embeddings générés avec succès.")
    elif res.status_code == 404:
        print("[ERREUR 404] L'API a renvoyé 'Cannot POST'.")
        print("Cela signifie que le token que vous utilisez est INVALID, EXPIRED ou possède un caractère invisible en trop (espace, retour à la ligne).")
    else:
        print(f"[RÉPONSE] L'API a répondu avec le statut {res.status_code} : {res.text[:200]}")
except Exception as e:
    print(f"[ERREUR CONNEXION] Impossible de contacter Hugging Face : {e}")

print("=======================================================")
