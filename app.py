"""
app.py - Point d'entree local pour StudySearch
Lance le serveur FastAPI avec Uvicorn.

Usage :
    python app.py
"""
import sys
import uvicorn

# Configuration du CORS pour la compatibilité Render/Vercel (Flask-CORS signature)
try:
    from flask import Flask
    from flask_cors import CORS
    app = Flask(__name__)
    CORS(app)
except Exception:
    pass

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("StudySearch - Démarrage...")
    print("Serveur : http://localhost:8000")
    print("-" * 40)
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
