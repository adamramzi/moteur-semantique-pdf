import os
import sys
import time
import sqlite3
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration de l'utilisateur de test pour prérequis de connexion
EMAIL_TEST = "kskdhjdjdjd24@gmail.com"
PASSWORD_TEST = "MotDePasse123!"

# Ajout du chemin de l'application locale pour interagir directement avec la base de données
sys.path.append(r"c:\Users\dell\Desktop\moteur_semantique - Copie")
from database import creer_utilisateur, valider_email

@pytest.fixture
def driver():
    """
    Fixture pytest pour initialiser et fermer le WebDriver Chrome proprement.
    Elle résout le chemin vers chromedriver.exe à la racine du projet.
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Optionnel: décommenter pour exécuter en mode sans interface (headless)
    # chrome_options.add_argument("--headless")
    
    # Résolution dynamique du chemin absolu de chromedriver.exe (4 niveaux car dans tests/UI/UI-05/test_UI_05.py)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    chromedriver_path = os.path.join(base_dir, "chromedriver.exe")
    
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_recherche_historique_succes(driver):
    """
    [ UI-05 ] - Recherche historique (Succès) :
    Vérifie qu'un message envoyé dans le chat contenant un mot-clé spécifique
    est bien indexé dans l'historique et peut être retrouvé via le moteur de recherche interne.
    """
    base_url = "http://localhost:5000/"
    
    # ── Prérequis : Garantir l'existence de l'utilisateur en base
    db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = ?", (EMAIL_TEST.lower(),))
        conn.commit()
        
    res_creation = creer_utilisateur(EMAIL_TEST, PASSWORD_TEST, "Adam Ramzi", "127.0.0.1")
    assert res_creation["succes"]
    res_validation = valider_email(EMAIL_TEST, res_creation["code_verification"])
    assert res_validation["succes"]

    # Connecter l'utilisateur
    driver.get(base_url)
    wait = WebDriverWait(driver, 10)
    
    try:
        start_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-home-start")))
        start_btn.click()
    except Exception:
        pass
        
    wait.until(EC.visibility_of_element_located((By.ID, "login-form")))
    
    driver.find_element(By.ID, "login-email").send_keys(EMAIL_TEST)
    driver.find_element(By.ID, "login-password").send_keys(PASSWORD_TEST)
    driver.find_element(By.ID, "btn-login").click()
    
    # Attendre que le tableau de bord soit actif
    wait.until(lambda d: "active" in d.find_element(By.ID, "dashboard-screen").get_attribute("class"))

    # ── Prérequis CRITIQUE : Créer et uploader un fichier temporaire pour pouvoir utiliser le chat
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dummy_file_path = os.path.join(current_dir, "dummy_akkodis.txt")
    with open(dummy_file_path, "w", encoding="utf-8") as f:
        f.write("Akkodis est un groupe leader dans le domaine du conseil en ingénierie et des services numériques.")

    try:
        # Trouver l'input de fichier masqué et lui envoyer le chemin du fichier temporaire
        file_input = driver.find_element(By.ID, "file-input")
        file_input.send_keys(dummy_file_path)
        
        # Cliquer sur "Analyser et enregistrer"
        btn_upload = wait.until(EC.element_to_be_clickable((By.ID, "btn-upload")))
        btn_upload.click()
        
        # Attendre que l'analyse soit finie (le dropdown du chat doit être activé)
        wait.until(lambda d: d.find_element(By.ID, "chat-pdf-select").is_enabled())

        # Taper le mot-clé très spécifique dans la barre de chat du Dashboard
        chat_input = wait.until(EC.visibility_of_element_located((By.ID, "chat-input")))
        chat_input.clear()
        chat_input.send_keys("Akkodis")
        
        # Cliquer sur le bouton d'envoi
        btn_send = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-send-gemini")))
        btn_send.click()
        
        # Attendre environ 2 secondes pour l'enregistrement du message dans l'historique local
        time.sleep(2)

        # ── Étape 1 : Ouvrir la modale des paramètres (⚙️)
        settings_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-logout-icon")))
        settings_btn.click()
        
        # Attendre la modale
        def check_modal_visible(d):
            try:
                modal = d.find_element(By.ID, "settings-modal")
                return "hidden" not in modal.get_attribute("class") and modal.is_displayed()
            except Exception:
                return False
        wait.until(check_modal_visible)

        # ── Étape 2 : Saisir le mot-clé exact ("Akkodis") dans le champ de recherche (#search-history-input)
        search_input = wait.until(EC.visibility_of_element_located((By.ID, "search-history-input")))
        search_input.clear()
        search_input.send_keys("Akkodis")

        # ── Étape 3 : Cliquer sur le bouton de recherche (loupe)
        btn_search = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-search-history")))
        btn_search.click()

        # ── Étape 4 (Assertion UI) : Attendre l'apparition de la page des résultats (#search-results-screen)
        # Attendre que la modale se ferme
        wait.until(lambda d: "hidden" in d.find_element(By.ID, "settings-modal").get_attribute("class"))
        
        # Attendre que l'écran des résultats soit visible
        wait.until(EC.visibility_of_element_located((By.ID, "search-results-screen")))
        
        search_screen = driver.find_element(By.ID, "search-results-screen")
        assert search_screen.is_displayed(), "Erreur : L'écran de recherche d'historique ne s'est pas affiché."

        # ── Étape 5 (Assertion de Résultat) : Vérifier qu'au moins un élément HTML portant la classe .result-card est présent
        results_container = driver.find_element(By.ID, "full-search-results")
        wait.until(lambda d: d.find_element(By.ID, "full-search-results").text.strip() != "")
        
        cards = results_container.find_elements(By.CLASS_NAME, "result-card")
        print(f"Nombre de cartes trouvées : {len(cards)}")
        
        assert len(cards) >= 1, "Erreur : Aucun résultat trouvé dans la recherche d'historique pour le mot-clé 'Akkodis'."

    finally:
        # Nettoyage du fichier temporaire à la fin du test
        if os.path.exists(dummy_file_path):
            os.remove(dummy_file_path)
