"""
test_evaluation.py
──────────────────
Évalue le moteur de recherche avec 5 questions sur le PDF indexé.
Affiche les résultats dans la console et les sauvegarde dans resultats_tests.txt
"""

import os
import sys
from datetime import datetime
from vectoriser import charger_index, rechercher
from sentence_transformers import SentenceTransformer

# Fix encodage Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
INDEX_DIR = "index_faiss"
FICHIER_RESULTATS = "resultats_tests.txt"
TOP_K = 1  # On prend le meilleur passage pour chaque question

# 5 questions de test variées
QUESTIONS = [
    "De quoi parle ce document ?",
    "Quels sont les principaux sujets abordés ?",
    "Quelle est la conclusion ou le résumé ?",
    "Quelles sont les informations importantes mentionnées ?",
    "Y a-t-il des données ou chiffres clés dans ce document ?",
]

# ──────────────────────────────────────────────
# Séparateurs visuels
# ──────────────────────────────────────────────
SEP_EPAIS  = "=" * 70
SEP_FIN    = "-" * 70


def ligne(texte=""):
    """Affiche et retourne une ligne de texte."""
    print(texte)
    return texte + "\n"


def evaluer():
    lignes_rapport = []

    def log(texte=""):
        print(texte)
        lignes_rapport.append(texte)

    # ── En-tête ──────────────────────────────────────────────────────────
    log(SEP_EPAIS)
    log("  RAPPORT D'ÉVALUATION — MOTEUR DE RECHERCHE SÉMANTIQUE")
    log(f"  Date : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")
    log(SEP_EPAIS)
    log()

    # ── Chargement de l'index ─────────────────────────────────────────────
    log("📂 Chargement de la base de recherche depuis le disque…")
    vecteurs, passages = charger_index(INDEX_DIR)

    if vecteurs is None or passages is None:
        msg = (
            "❌ Aucune base de recherche trouvée !\n"
            "   → Veuillez d'abord lancer app.py et analyser un fichier PDF."
        )
        log(msg)
        return

    log(f"✅ Base chargée avec succès : {len(passages)} passages disponibles")
    log()

    # ── Chargement du modèle ──────────────────────────────────────────────
    log("🧠 Chargement du moteur d'analyse de texte (all-mpnet-base-v2)…")
    model = SentenceTransformer("all-mpnet-base-v2")
    log("✅ Moteur prêt (modèle amélioré)")
    log()

    # ── Tests ─────────────────────────────────────────────────────────────
    log(SEP_EPAIS)
    log("  RÉSULTATS DES 5 QUESTIONS")
    log(SEP_EPAIS)

    scores = []

    for i, question in enumerate(QUESTIONS, start=1):
        log()
        log(f"  Question {i} / {len(QUESTIONS)}")
        log(SEP_FIN)
        log(f"  ❓ {question}")
        log()

        # Encodage + recherche
        vecteur_question = model.encode([question])[0]
        resultats = rechercher(vecteur_question, vecteurs, passages, top_k=TOP_K)

        if not resultats:
            log("  ⚠️ Aucun passage trouvé pour cette question.")
            continue

        meilleur = resultats[0]
        score_pct = meilleur["score"] * 100
        num_passage = meilleur["chunk_index"] + 1
        texte = meilleur["texte"]

        # Tronquer l'affichage si trop long
        texte_affiche = texte if len(texte) <= 400 else texte[:400] + "…"

        log(f"  📄 Passage trouvé : #{num_passage}")
        log(f"  📊 Score de correspondance : {score_pct:.1f}%")
        log()
        log("  Contenu du passage :")
        # Indenter chaque ligne du passage
        for sous_ligne in texte_affiche.split(". "):
            log(f"    {sous_ligne.strip()}")
        log()

        scores.append(score_pct)

    # ── Score moyen ───────────────────────────────────────────────────────
    log()
    log(SEP_EPAIS)
    log("  BILAN GLOBAL")
    log(SEP_EPAIS)

    if scores:
        score_moyen = sum(scores) / len(scores)
        score_min   = min(scores)
        score_max   = max(scores)

        log(f"  Nombre de questions testées : {len(scores)}")
        log(f"  Score moyen de correspondance : {score_moyen:.1f}%")
        log(f"  Score minimum                 : {score_min:.1f}%")
        log(f"  Score maximum                 : {score_max:.1f}%")
        log()

        # Comparaison avec l'ancien score
        ancien_score = 25.2
        diff = score_moyen - ancien_score
        signe = "+" if diff >= 0 else ""
        log(f"  📊 Ancien score moyen (MiniLM, chunks 200 mots) : {ancien_score:.1f}%")
        log(f"  📊 Nouveau score moyen (mpnet, chunks 100+overlap) : {score_moyen:.1f}%")
        log(f"  📈 Évolution : {signe}{diff:.1f} points")
        log()

        # Évaluation qualitative
        if score_moyen >= 70:
            log("  ✅ Excellent ! Le moteur répond très bien aux questions.")
        elif score_moyen >= 50:
            log("  👍 Bon résultat. Le moteur trouve des passages pertinents.")
        elif score_moyen >= 30:
            log("  ⚠️ Résultat moyen. Le document est peut-être trop court ou peu varié.")
        else:
            log("  ❌ Faible résultat. Essayez avec un document plus riche en contenu.")
    else:
        log("  ⚠️ Aucun score calculé (aucun résultat retourné).")

    log()
    log(SEP_EPAIS)

    # ── Sauvegarde ────────────────────────────────────────────────────────
    with open(FICHIER_RESULTATS, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes_rapport))

    print()
    print(f"💾 Résultats sauvegardés dans : {os.path.abspath(FICHIER_RESULTATS)}")


if __name__ == "__main__":
    evaluer()
