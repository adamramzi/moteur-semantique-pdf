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

# Variables de configuration modifiables
EMAIL_TEST = "kskdhjdjdjd24@gmail.com"
PASSWORD_TEST = "MotDePasse123!"

# Ajout du chemin de l'application locale pour interagir directement avec la base de données
sys.path.append(r"c:\Users\dell\Desktop\moteur_semantique - Copie")
from database import creer_utilisateur, valider_email

@pytest.fixture
def driver():
    """
    Fixture pytest pour initialiser et fermer le WebDriver Chrome proprement.
    Elle résout le chemin vers chromedriver.exe à la racine de l'espace de travail.
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

def test_connexion_reussie(driver):
    """
    [ AUTH-03 ] - Connexion réussie :
    Vérifie la connexion réussie de l'utilisateur, le basculement d'interface (UI)
    et le stockage correct des jetons de sécurité dans le localStorage du navigateur.
    """
    base_url = "http://localhost:5000/"
    
    # ── Prérequis : Garantir que l'utilisateur de test existe, est vérifié et possède le bon mot de passe en base
    db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # On supprime l'utilisateur s'il existe déjà afin de réinitialiser son état proprement
        cursor.execute("DELETE FROM users WHERE email = ?", (EMAIL_TEST.lower(),))
        conn.commit()
        
    # Création du compte de test à la volée
    res_creation = creer_utilisateur(EMAIL_TEST, PASSWORD_TEST, "Utilisateur Test LocalStorage", "127.0.0.1")
    assert res_creation["succes"], f"Échec de la création de l'utilisateur en base : {res_creation.get('erreur')}"
    
    # Validation du compte de test (mise à jour de est_verifie à 1)
    res_validation = valider_email(EMAIL_TEST, res_creation["code_verification"])
    assert res_validation["succes"], f"Échec de la validation de l'utilisateur : {res_validation.get('erreur')}"

    # ── Étape 1 : Charger l'application http://localhost:5000/
    driver.get(base_url)
    wait = WebDriverWait(driver, 10)
    
    # Cliquer sur le bouton d'accueil "Commencer maintenant" si l'écran de présentation d'accueil est actif
    try:
        start_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-home-start")))
        start_btn.click()
    except Exception:
        # Déjà sur l'écran d'authentification
        pass
        
    # S'assurer que le formulaire de connexion (#login-form) est bien actif/visible
    wait.until(EC.visibility_of_element_located((By.ID, "login-form")))
    
    # Si par hasard l'interface est restée sur l'onglet inscription, on bascule vers le formulaire de connexion
    try:
        if not driver.find_element(By.ID, "login-form").is_displayed():
            btn_back_login = driver.find_element(By.ID, "link-back-login-reg")
            btn_back_login.click()
            wait.until(EC.visibility_of_element_located((By.ID, "login-form")))
    except Exception:
        pass

    # ── Étape 2 : Localiser le champ Email de connexion et y injecter l'adresse de test
    login_email_field = driver.find_element(By.ID, "login-email")
    login_email_field.clear()
    login_email_field.send_keys(EMAIL_TEST)

    # ── Étape 3 : Localiser le champ Mot de passe de connexion et y injecter le mot de passe correspondant
    login_password_field = driver.find_element(By.ID, "login-password")
    login_password_field.clear()
    login_password_field.send_keys(PASSWORD_TEST)

    # ── Étape 4 : Cliquer sur le bouton "Se connecter"
    btn_login = driver.find_element(By.ID, "btn-login")
    btn_login.click()

    # ── Étape 5 (Assertion UI) : Attendre que l'interface bascule et vérifier que l'élément #dashboard-screen devient visible (ou acquiert la classe .active)
    def check_dashboard_active(d):
        try:
            dashboard = d.find_element(By.ID, "dashboard-screen")
            return "active" in dashboard.get_attribute("class") or dashboard.is_displayed()
        except Exception:
            return False
            
    wait.until(check_dashboard_active)
    
    dashboard_element = driver.find_element(By.ID, "dashboard-screen")
    classes = dashboard_element.get_attribute("class")
    assert "active" in classes or dashboard_element.is_displayed(), "Le tableau de bord ne s'est pas affiché après connexion."

    # ── Étape 6 (Assertion LocalStorage) : Utiliser driver.execute_script() pour lire le localStorage et valider le token et l'email
    # Lecture des valeurs stockées dans le localStorage du navigateur
    local_storage_token = driver.execute_script("return localStorage.getItem('token');")
    local_storage_user_email = driver.execute_script("return localStorage.getItem('userEmail');")
    local_storage_email = driver.execute_script("return localStorage.getItem('email');")
    
    # Débogage console pytest
    print(f"Token stocké : {local_storage_token}")
    print(f"userEmail stocké : {local_storage_user_email}")
    print(f"email stocké : {local_storage_email}")

    # Vérification que le token de connexion existe et n'est pas vide/nul
    assert local_storage_token is not None, "Le token d'authentification n'a pas été stocké dans le localStorage."
    assert len(local_storage_token) > 0, "Le token stocké est vide."
    
    # Vérification que les clés de l'e-mail correspondent bien à l'adresse de connexion
    assert local_storage_user_email == EMAIL_TEST, f"userEmail dans localStorage ({local_storage_user_email}) ne correspond pas à l'email saisi ({EMAIL_TEST})."
    assert local_storage_email == EMAIL_TEST, f"email dans localStorage ({local_storage_email}) ne correspond pas à l'email saisi ({EMAIL_TEST})."
