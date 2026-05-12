"""
app.py - Point d'entree local pour le Moteur Semantique PDF
Lance le serveur FastAPI avec Uvicorn.

Usage :
    python app.py
"""
import sys
import uvicorn

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("Moteur Semantique PDF - Demarrage...")
    print("Serveur : http://localhost:8000")
    print("-" * 40)
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
