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

def test_recherche_historique_vide(driver):
    """
    [ UI-04 ] - Recherche historique (Vide) :
    Vérifie que la recherche de termes inexistants/absurdes dans l'historique ferme
    la modale de configuration, bascule vers l'écran des résultats de recherche
    et affiche le message approprié sans carte de résultats.
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

    # ── Étape 1 : Cliquer sur le bouton des paramètres (⚙️) pour ouvrir la modale
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

    # ── Étape 2 : Localiser le champ de recherche (#search-history-input) et y injecter une chaîne absurde
    search_input = wait.until(EC.visibility_of_element_located((By.ID, "search-history-input")))
    search_input.clear()
    search_input.send_keys("xyzazerty")

    # ── Étape 3 : Cliquer sur le bouton de recherche (loupe) associé
    btn_search = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-search-history")))
    btn_search.click()

    # ── Étape 4 (Assertion de redirection) : Vérifier que la modale se ferme et que l'écran des résultats (#search-results-screen) s'affiche
    # Attendre que la modale soit masquée
    wait.until(lambda d: "hidden" in d.find_element(By.ID, "settings-modal").get_attribute("class"))
    
    # Attendre que l'écran des résultats soit visible
    wait.until(EC.visibility_of_element_located((By.ID, "search-results-screen")))
    
    search_screen = driver.find_element(By.ID, "search-results-screen")
    settings_modal = driver.find_element(By.ID, "settings-modal")
    
    assert search_screen.is_displayed(), "Erreur : L'écran de recherche d'historique ne s'est pas affiché."
    assert "hidden" in settings_modal.get_attribute("class"), "Erreur : La modale des paramètres est restée ouverte."

    # ── Étape 5 (Assertion UI) : Vérifier que le conteneur (#full-search-results) est vide de cartes et contient le message de vacuité
    results_container = driver.find_element(By.ID, "full-search-results")
    
    # Attendre que le conteneur se mette à jour
    wait.until(lambda d: d.find_element(By.ID, "full-search-results").text.strip() != "")
    
    # Extraire le texte et les éléments enfants
    cards = results_container.find_elements(By.CLASS_NAME, "result-card")
    container_text = results_container.text
    
    print(f"Nombre de cartes trouvées : {len(cards)}")
    print(f"Texte du conteneur de résultats : '{container_text}'")
    
    # Le conteneur ne doit pas avoir de cartes
    assert len(cards) == 0, f"Erreur : Des cartes de résultats ont été affichées ({len(cards)}) pour une recherche absurde."
    # Le message attendu doit être présent
    assert "Aucun résultat trouvé" in container_text, f"Erreur : Le message d'absence de résultats n'est pas affiché ou est incorrect : '{container_text}'."
