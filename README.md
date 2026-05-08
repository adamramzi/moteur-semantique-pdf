# 🔍 Moteur de recherche sémantique de documents PDF

Une application web qui permet de rechercher intelligemment dans vos fichiers PDF en posant des questions en langage naturel.

## ✨ Fonctionnalités

- 📤 **Upload de PDFs** — Importez un ou plusieurs fichiers PDF
- 🧠 **Analyse automatique** — Le texte est extrait et analysé automatiquement
- 🔎 **Recherche intelligente** — Posez une question, trouvez les passages les plus pertinents
- 📊 **Score de correspondance** — Chaque résultat affiche son pourcentage de pertinence
- 🕐 **Historique des recherches** — Les 5 dernières recherches sont mémorisées
- 💾 **Export des résultats** — Téléchargez vos résultats en fichier texte
- 🔄 **Chargement automatique** — L'index est rechargé au démarrage sans re-uploader

## 🛠️ Technologies utilisées

| Composant | Rôle |
|---|---|
| `sentence-transformers` | Analyse et compréhension du texte (`all-MiniLM-L6-v2`) |
| `numpy` | Calcul de similarité (cosinus) |
| `pymupdf` | Extraction de texte depuis les PDFs |
| `streamlit` | Interface web interactive |

## 🚀 Installation et lancement

```bash
# 1. Cloner le projet
git clone https://github.com/VOTRE_USERNAME/moteur-semantique-pdf.git
cd moteur-semantique-pdf

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer l'application
streamlit run app.py
```

L'application s'ouvre automatiquement sur `http://localhost:8501`

## 📁 Structure du projet

```
moteur-semantique-pdf/
├── app.py                # Interface principale Streamlit
├── pdf_processor.py      # Extraction et découpage du texte PDF
├── vectoriser.py         # Vectorisation et recherche par similarité
├── test_evaluation.py    # Script d'évaluation avec 5 questions
├── requirements.txt      # Dépendances Python
└── .gitignore
```

## 📖 Utilisation

1. Ouvrez l'application dans votre navigateur
2. **Ajoutez vos fichiers PDF** dans la section "Ajouter vos fichiers PDF"
3. Cliquez sur **"Analyser et enregistrer les documents"**
4. Dans la section "Poser une question", écrivez votre question
5. Cliquez sur **"Rechercher"** et consultez les passages trouvés
6. Téléchargez les résultats si besoin

## 🧪 Évaluation

Pour tester les performances du moteur sur votre PDF indexé :

```bash
python test_evaluation.py
```

Les résultats sont sauvegardés dans `resultats_tests.txt`.
