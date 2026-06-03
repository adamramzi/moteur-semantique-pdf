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

# Variables de configuration
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

def test_verification_avatar(driver):
    """
    [ AUTH-04 ] - Vérification de l'Avatar :
    Vérifie la bonne génération de l'avatar utilisateur en extrayant la première lettre
    de son prénom ("Adam" -> "A") après connexion.
    """
    base_url = "http://localhost:5000/"
    
    # ── Prérequis : Enregistrer et valider le compte "Adam Ramzi" en base de données SQLite locale
    db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Supprimer le compte existant pour s'assurer d'insérer les nouvelles métadonnées
        cursor.execute("DELETE FROM users WHERE email = ?", (EMAIL_TEST.lower(),))
        conn.commit()
        
    # Création du compte de test sous le nom complet "Adam Ramzi"
    res_creation = creer_utilisateur(EMAIL_TEST, PASSWORD_TEST, "Adam Ramzi", "127.0.0.1")
    assert res_creation["succes"], f"Échec de la création de l'utilisateur : {res_creation.get('erreur')}"
    
    # Validation par code de sécurité
    res_validation = valider_email(EMAIL_TEST, res_creation["code_verification"])
    assert res_validation["succes"], f"Échec de la validation de l'utilisateur : {res_validation.get('erreur')}"

    # ── Connexion de l'utilisateur de test sur l'application StudySearch
    driver.get(base_url)
    wait = WebDriverWait(driver, 10)
    
    # Passage de l'écran d'accueil si actif
    try:
        start_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-home-start")))
        start_btn.click()
    except Exception:
        pass
        
    # S'assurer d'être sur le formulaire de connexion
    wait.until(EC.visibility_of_element_located((By.ID, "login-form")))
    
    # Remplir et valider les identifiants
    login_email_field = driver.find_element(By.ID, "login-email")
    login_email_field.clear()
    login_email_field.send_keys(EMAIL_TEST)

    login_password_field = driver.find_element(By.ID, "login-password")
    login_password_field.clear()
    login_password_field.send_keys(PASSWORD_TEST)

    btn_login = driver.find_element(By.ID, "btn-login")
    btn_login.click()

    # ── Étape 1 : Attendre explicitement que l'écran du tableau de bord (#dashboard-screen) devienne visible ou actif
    def check_dashboard_active(d):
        try:
            dashboard = d.find_element(By.ID, "dashboard-screen")
            return "active" in dashboard.get_attribute("class") or dashboard.is_displayed()
        except Exception:
            return False
            
    wait.until(check_dashboard_active)

    # ── Étape 2 : Localiser l'élément HTML correspondant à l'avatar de l'utilisateur (ID attendu : #user-avatar)
    avatar_element = driver.find_element(By.ID, "user-avatar")

    # ── Étape 3 : Attendre que cet élément ne soit pas vide (le temps que le JS charge la première lettre)
    wait.until(lambda d: d.find_element(By.ID, "user-avatar").text.strip() != "")

    # ── Étape 4 (Assertion) : Extraire le texte de l'avatar et vérifier qu'il est égal à "A" (première lettre d'Adam)
    avatar_text = avatar_element.text.strip()
    print(f"Lettre affichée dans l'avatar : '{avatar_text}'")
    
    assert avatar_text == "A", f"Erreur : L'avatar affiche '{avatar_text}' au lieu de la lettre attendue 'A'."
