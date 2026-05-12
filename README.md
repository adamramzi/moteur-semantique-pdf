# 🔍 Moteur de recherche sémantique de documents PDF

Une application web qui permet de rechercher intelligemment dans vos fichiers PDF en posant des questions en langage naturel.
Entièrement repensée pour fonctionner sur Vercel avec une architecture Serverless.

## ✨ Fonctionnalités

- 📤 **Upload de PDFs** — Importez un ou plusieurs fichiers PDF
- 🧠 **Analyse automatique** — Le texte est extrait et analysé automatiquement via l'API HuggingFace
- 🔎 **Recherche intelligente** — Posez une question, trouvez les passages les plus pertinents
- 🔐 **Authentification** — Système de comptes utilisateurs avec code de vérification par email
- 📊 **Historique par utilisateur** — Les recherches et documents sont privés et sauvegardés
- 🚀 **Compatible Vercel** — Architecture FastAPI prête pour un déploiement gratuit

## 🛠️ Technologies utilisées

| Composant | Rôle |
|---|---|
| `FastAPI` | Backend API (routes, sécurité, endpoints) |
| `HuggingFace API` | Modèle `all-mpnet-base-v2` pour la vectorisation sans surcharger le serveur |
| `SQLite` / `JWT` | Base de données locale pour la gestion des utilisateurs et authentification sécurisée |
| `Brevo` | Envoi des emails de vérification |
| `HTML/CSS/JS Vanilla` | Frontend moderne, rapide et responsive |

## 🚀 Lancement en local

1. **Cloner le projet**
2. **Installer les dépendances** : `pip install -r requirements.txt`
3. **Créer un fichier `.env`** avec vos clés : `HF_API_TOKEN`, `BREVO_API_KEY`, `EMAIL_SENDER`
4. **Lancer le serveur** : `python app.py` (ou `uvicorn api.index:app --reload`)
5. Ouvrez `http://localhost:8000`

## ☁️ Déploiement sur Vercel

Le projet est préconfiguré pour Vercel grâce au fichier `vercel.json` utilisant les réécritures (`rewrites`).
Il suffit d'importer le projet sur le tableau de bord Vercel et de configurer vos variables d'environnement. Le dossier `public/` sera servi automatiquement.
