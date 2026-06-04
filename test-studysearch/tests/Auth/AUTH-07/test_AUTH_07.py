import os
import time
import sqlite3
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def test_suppression_compte_confirmation(driver):
    """
    [ AUTH-07 ] - Suppression du compte (Confirmation) :
    Crée un compte jetable via le formulaire d'inscription, le valide, se connecte,
    valide la suppression définitive de son compte et s'assure que toutes ses sessions
    et informations locales sont effacées de l'application.
    """
    base_url = "http://localhost:5000/"
    
    # ── Prérequis : Générer un compte jetable unique
    timestamp = int(time.time())
    email_jetable = f"delete_me_{timestamp}@test.local"
    mot_de_passe = "MotDePasse123!"
    nom_complet = "Jetable Test"

    driver.get(base_url)
    wait = WebDriverWait(driver, 15)
    
    # Passer l'écran d'accueil
    try:
        start_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-home-start")))
        start_btn.click()
    except Exception:
        pass
        
    # Accéder au formulaire d'inscription
    go_register_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-go-register")))
    go_register_btn.click()
    
    # Remplir le formulaire d'inscription
    wait.until(EC.visibility_of_element_located((By.ID, "register-fullname"))).send_keys(nom_complet)
    driver.find_element(By.ID, "reg-email").send_keys(email_jetable)
    driver.find_element(By.ID, "reg-password").send_keys(mot_de_passe)
    driver.find_element(By.ID, "reg-password2").send_keys(mot_de_passe)
    
    # Soumettre l'inscription
    driver.find_element(By.ID, "btn-register").click()
    
    # Attendre l'écran de vérification
    wait.until(EC.visibility_of_element_located((By.ID, "verify-code")))
    
    # Laisser le temps à la base SQLite d'enregistrer le code de vérification
    time.sleep(1.5)
    
    # Récupérer le code de vérification
    db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
    code_verification = None
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT code_verification FROM users WHERE email = ?", (email_jetable.lower(),))
        row = cursor.fetchone()
        if row:
            code_verification = row[0]
            
    assert code_verification is not None, "Impossible de récupérer le code de vérification du compte jetable."
    
    # Saisir le code et valider
    driver.find_element(By.ID, "verify-code").send_keys(str(code_verification))
    driver.find_element(By.ID, "btn-verify").click()
    
    # Attendre le retour automatique vers le formulaire de connexion
    wait.until(EC.visibility_of_element_located((By.ID, "login-form")))
    
    # Se connecter avec le compte jetable
    driver.find_element(By.ID, "login-email").send_keys(email_jetable)
    driver.find_element(By.ID, "login-password").send_keys(mot_de_passe)
    driver.find_element(By.ID, "btn-login").click()
    
    # Attendre que le tableau de bord soit actif
    wait.until(lambda d: "active" in d.find_element(By.ID, "dashboard-screen").get_attribute("class"))

    # ── Étape 1 : Cliquer sur le bouton des paramètres (⚙️) et attendre la modale
    settings_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-logout-icon")))
    settings_btn.click()
    
    def check_modal_visible(d):
        try:
            modal = d.find_element(By.ID, "settings-modal")
            classes = modal.get_attribute("class")
            return "hidden" not in classes and modal.is_displayed()
        except Exception:
            return False
    wait.until(check_modal_visible)

    # ── Étape 2 : Cliquer sur le bouton "Supprimer mon compte"
    delete_account_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[onclick='deleteAccount()']")))
    delete_account_btn.click()

    # ── Étape 3 : Basculer sur l'alerte de confirmation native et valider (accept)
    # L'application affiche un premier confirm() demandant de confirmer la suppression irréversible.
    wait.until(EC.alert_is_present())
    confirm_alert = driver.switch_to.alert
    print(f"Première alerte (Confirmation) interceptée : '{confirm_alert.text}'")
    confirm_alert.accept()
    
    # L'application affiche ensuite un second alert() pour confirmer le succès de la suppression.
    wait.until(EC.alert_is_present())
    success_alert = driver.switch_to.alert
    print(f"Deuxième alerte (Succès) interceptée : '{success_alert.text}'")
    success_alert.accept()

    # ── Étape 4 (Assertion de redirection) : Attendre la redirection sur l'écran d'accueil (#home-screen)
    def check_home_screen_active(d):
        try:
            home_screen = d.find_element(By.ID, "home-screen")
            modal = d.find_element(By.ID, "settings-modal")
            return "active" in home_screen.get_attribute("class") and "hidden" in modal.get_attribute("class")
        except Exception:
            return False
            
    wait.until(check_home_screen_active)
    
    home_screen = driver.find_element(By.ID, "home-screen")
    assert "active" in home_screen.get_attribute("class"), "L'utilisateur n'a pas été redirigé vers la page d'accueil."

    # ── Étape 5 (Assertion de session) : Vérifier que le localStorage est totalement vide
    local_storage_token = driver.execute_script("return localStorage.getItem('token');")
    local_storage_user_email = driver.execute_script("return localStorage.getItem('userEmail');")
    
    print(f"Token stocké après suppression : {local_storage_token}")
    print(f"Email stocké après suppression : {local_storage_user_email}")
    
    assert local_storage_token is None or local_storage_token == "", "Erreur : Le token de session n'a pas été supprimé du localStorage."
    assert local_storage_user_email is None or local_storage_user_email == "", "Erreur : Les informations de session utilisateur n'ont pas été vidées."
