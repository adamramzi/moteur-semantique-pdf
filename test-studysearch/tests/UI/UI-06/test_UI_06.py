import os
import sys
import time
import sqlite3
import pytest
from selenium import webdriver
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
    Elle utilise Selenium Manager pour configurer ChromeDriver en mode headless.
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_scroll_dynamique_recherche(driver):
    """
    [ UI-06 ] - Scroll dynamique depuis la recherche :
    Vérifie qu'en cliquant sur une carte de résultat de recherche, l'écran de résultats
    se ferme, le dashboard redevient actif, et le message ciblé est mis en valeur avec la classe .highlight-msg.
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

    # Création du fichier temporaire à uploader
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dummy_file_path = os.path.join(current_dir, "dummy_akkodis.txt")
    with open(dummy_file_path, "w", encoding="utf-8") as f:
        f.write("Akkodis est un groupe leader dans le domaine du conseil en ingénierie et des services numériques.")

    try:
        # Uploader le fichier temporaire pour activer le chat
        file_input = driver.find_element(By.ID, "file-input")
        file_input.send_keys(dummy_file_path)
        
        btn_upload = wait.until(EC.element_to_be_clickable((By.ID, "btn-upload")))
        btn_upload.click()
        
        # Attendre la fin de l'upload (dropdown activé)
        wait.until(lambda d: d.find_element(By.ID, "chat-pdf-select").is_enabled())

        # Taper le mot-clé dans la barre de chat du Dashboard
        chat_input = wait.until(EC.visibility_of_element_located((By.ID, "chat-input")))
        chat_input.clear()
        chat_input.send_keys("Akkodis")
        
        # Envoyer le message
        btn_send = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-send-gemini")))
        btn_send.click()
        
        # Attendre environ 2 secondes la persistance locale
        time.sleep(2)

        # Ouvrir la modale des paramètres (⚙️)
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

        # Saisir le mot-clé exact ("Akkodis") dans le champ de recherche
        search_input = wait.until(EC.visibility_of_element_located((By.ID, "search-history-input")))
        search_input.clear()
        search_input.send_keys("Akkodis")

        # Cliquer sur le bouton de recherche (loupe)
        btn_search = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-search-history")))
        btn_search.click()

        # Attendre l'apparition de l'écran des résultats
        wait.until(lambda d: "hidden" in d.find_element(By.ID, "settings-modal").get_attribute("class"))
        wait.until(EC.visibility_of_element_located((By.ID, "search-results-screen")))
        
        results_container = driver.find_element(By.ID, "full-search-results")
        wait.until(lambda d: d.find_element(By.ID, "full-search-results").text.strip() != "")
        
        # S'assurer d'avoir au moins une carte de résultat
        cards = results_container.find_elements(By.CLASS_NAME, "result-card")
        assert len(cards) >= 1, "Erreur : Aucune carte de résultat trouvée pour le mot-clé 'Akkodis'."

        # ── Étape 1 : Localiser la première carte de résultat affichée et cliquer dessus
        first_card = cards[0]
        first_card.click()

        # ── Étape 2 (Assertion de navigation) : Vérifier que l'écran des résultats n'est plus visible et le Dashboard actif
        wait.until(lambda d: not d.find_element(By.ID, "search-results-screen").is_displayed())
        wait.until(lambda d: "active" in d.find_element(By.ID, "dashboard-screen").get_attribute("class"))

        # ── Étape 3 (Assertion de surbrillance) : Vérifier la présence de la classe CSS .highlight-msg
        highlighted_element = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "highlight-msg"))
        )
        assert highlighted_element is not None, "Erreur : Le message ciblé n'a pas reçu la classe .highlight-msg."

    finally:
        # Nettoyage du fichier temporaire
        if os.path.exists(dummy_file_path):
            os.remove(dummy_file_path)
