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

# Configuration du compte de test
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
    
    # Résolution dynamique du chemin absolu de chromedriver.exe
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    chromedriver_path = os.path.join(base_dir, "chromedriver.exe")
    
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_deconnexion(driver):
    """
    [ AUTH-05 ] - Déconnexion depuis les paramètres :
    Valide que la déconnexion ferme la session utilisateur, redirige vers l'accueil,
    et efface le jeton d'authentification du localStorage.
    """
    base_url = "http://localhost:5000/"
    
    # ── Prérequis : Garantir que l'utilisateur de test existe et est validé en base de données locale
    db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = ?", (EMAIL_TEST.lower(),))
        conn.commit()
        
    res_creation = creer_utilisateur(EMAIL_TEST, PASSWORD_TEST, "Adam Ramzi", "127.0.0.1")
    assert res_creation["succes"]
    res_validation = valider_email(EMAIL_TEST, res_creation["code_verification"])
    assert res_validation["succes"]

    # ── Prérequis : Connecter l'utilisateur et s'assurer que l'écran dashboard est actif
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
    
    # Attendre que l'écran du tableau de bord soit actif
    wait.until(lambda d: "active" in d.find_element(By.ID, "dashboard-screen").get_attribute("class"))

    # ── Étape 1 : Localiser et cliquer sur le bouton des paramètres (l'icône d'engrenage #btn-logout-icon)
    settings_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-logout-icon")))
    settings_btn.click()

    # ── Étape 2 : Attendre que la modale #settings-modal devienne visible (qu'elle perde la classe .hidden)
    def check_modal_visible(d):
        try:
            modal = d.find_element(By.ID, "settings-modal")
            classes = modal.get_attribute("class")
            return "hidden" not in classes and modal.is_displayed()
        except Exception:
            return False
            
    wait.until(check_modal_visible)

    # ── Étape 3 : Localiser le bouton "Se déconnecter" dans la modale et cliquer dessus
    # On le localise via sa propriété onclick="logout()" ou via son texte
    logout_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[onclick='logout()']")))
    logout_btn.click()

    # ── Étape 4 (Assertion UI) : Vérifier que la modale est fermée et redirection vers l'accueil (#home-screen visible/actif)
    def check_home_screen_active(d):
        try:
            home_screen = d.find_element(By.ID, "home-screen")
            modal = d.find_element(By.ID, "settings-modal")
            return "active" in home_screen.get_attribute("class") and "hidden" in modal.get_attribute("class")
        except Exception:
            return False

    wait.until(check_home_screen_active)

    home_screen = driver.find_element(By.ID, "home-screen")
    modal_element = driver.find_element(By.ID, "settings-modal")
    
    assert "active" in home_screen.get_attribute("class"), "L'utilisateur n'a pas été redirigé vers l'écran d'accueil après déconnexion."
    assert "hidden" in modal_element.get_attribute("class"), "La modale des paramètres est restée ouverte après déconnexion."

    # ── Étape 5 (Assertion Sécurité) : Vérifier que le localStorage ne contient plus le token
    local_storage_token = driver.execute_script("return localStorage.getItem('token');")
    local_storage_user_email = driver.execute_script("return localStorage.getItem('userEmail');")
    
    print(f"Jeton de session après déconnexion : {local_storage_token}")
    print(f"E-mail stocké après déconnexion : {local_storage_user_email}")

    assert local_storage_token is None or local_storage_token == "", "Erreur de sécurité : le token de session est toujours présent dans le localStorage après la déconnexion."
    assert local_storage_user_email is None or local_storage_user_email == "", "Erreur de sécurité : l'e-mail de l'utilisateur est toujours présent dans le localStorage après la déconnexion."
