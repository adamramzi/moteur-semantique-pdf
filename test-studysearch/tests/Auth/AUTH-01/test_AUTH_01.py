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
    # chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_inscription_reussie(driver):
    """
    [ AUTH-01 ] - Inscription réussie :
    Teste la création réussie d'un compte sur l'application StudySearch locale
    avec validation éventuelle par code à usage unique issu de la base SQLite.
    """
    base_url = "http://localhost:5000/"
    
    # ── Étape 1 : Charger http://localhost:5000/. S'assurer que le formulaire d'inscription est visible et prêt à être rempli.
    driver.get(base_url)
    wait = WebDriverWait(driver, 10)
    
    # Attendre et cliquer sur le bouton d'accueil si l'écran d'accueil de présentation s'affiche
    try:
        start_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-home-start")))
        start_btn.click()
    except Exception:
        # Si le bouton d'accueil n'est pas présent, on suppose qu'on est déjà sur l'écran d'authentification
        pass
        
    # Cliquer sur "Créer un nouveau compte" pour afficher le formulaire d'inscription
    go_register_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-go-register")))
    go_register_btn.click()
    
    # S'assurer que le champ de saisie du Nom Complet est visible
    nom_complet_field = wait.until(EC.visibility_of_element_located((By.ID, "register-fullname")))
    
    # ── Étape 2 : Générer un email unique (ex: test_user_<timestamp>@studysearch.local) pour éviter les conflits lors d'exécutions multiples.
    timestamp = int(time.time())
    email_unique = f"test_user_{timestamp}@studysearch.local"
    
    # ── Étape 3 : Remplir le champ du Nom Complet avec "Utilisateur Test".
    nom_complet_field.send_keys("Utilisateur Test")
    
    # ── Étape 4 : Remplir le champ de l'email avec l'email unique généré.
    email_field = driver.find_element(By.ID, "reg-email")
    email_field.send_keys(email_unique)
    
    # ── Étape 5 : Remplir le champ du mot de passe avec "MotDePasse123!".
    # Nous remplissons également le champ de confirmation pour soumettre un formulaire valide
    password_field = driver.find_element(By.ID, "reg-password")
    password_field.send_keys("MotDePasse123!")
    
    confirm_password_field = driver.find_element(By.ID, "reg-password2")
    confirm_password_field.send_keys("MotDePasse123!")
    
    # ── Étape 6 : Cliquer sur le bouton de validation de l'inscription.
    submit_btn = driver.find_element(By.ID, "btn-register")
    submit_btn.click()
    
    # ── Étape intermédiaire optionnelle : Vérification par code de sécurité e-mail
    try:
        # Attendre que l'écran de vérification s'affiche (ou que la redirection ait déjà eu lieu si directe)
        WebDriverWait(driver, 5).until(
            lambda d: d.find_element(By.ID, "verify-screen").is_displayed() or 
                      "active" in d.find_element(By.ID, "dashboard-screen").get_attribute("class")
        )
        
        # Si l'écran de vérification par code de sécurité e-mail est affiché
        if driver.find_element(By.ID, "verify-screen").is_displayed():
            # Laisser un court instant au backend pour insérer l'utilisateur en base
            time.sleep(1.5)
            
            # On récupère le code de vérification directement dans la base SQLite locale
            db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
            code_verification = None
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT code_verification FROM users WHERE email = ?", (email_unique.lower(),))
                row = cursor.fetchone()
                if row:
                    code_verification = row[0]
            
            if code_verification:
                # Saisir le code de vérification récupéré
                verify_input = driver.find_element(By.ID, "verify-code")
                verify_input.send_keys(str(code_verification))
                
                # Valider le code de vérification
                btn_verify = driver.find_element(By.ID, "btn-verify")
                btn_verify.click()
                
                # Attendre que l'écran de connexion s'affiche
                WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "login-form"))
                )
                
                # Remplir les informations de connexion pour le nouvel utilisateur vérifié
                login_email = driver.find_element(By.ID, "login-email")
                login_email.send_keys(email_unique)
                
                login_password = driver.find_element(By.ID, "login-password")
                login_password.send_keys("MotDePasse123!")
                
                btn_login = driver.find_element(By.ID, "btn-login")
                btn_login.click()
    except Exception as e:
        # En cas d'erreur ou si la vérification est désactivée, on poursuit vers l'assertion finale
        print(f"[Info] Étape de vérification ignorée ou automatique : {e}")
        
    # ── Étape 7 (Assertion) : Attendre explicitement et vérifier que la connexion automatique ou la redirection a bien eu lieu.
    # Pour cela, vérifier que l'écran du tableau de bord (#dashboard-screen) acquiert la classe .active, OU vérifier la présence de l'avatar utilisateur en bas à gauche (#user-avatar).
    def check_dashboard_or_avatar(d):
        try:
            dashboard = d.find_element(By.ID, "dashboard-screen")
            if "active" in dashboard.get_attribute("class"):
                return True
        except Exception:
            pass
            
        try:
            avatar = d.find_element(By.ID, "user-avatar")
            if avatar.is_displayed():
                return True
        except Exception:
            pass
            
        return False
        
    # Attente explicite de la redirection finale vers le tableau de bord
    wait.until(check_dashboard_or_avatar)
    
    # Vérification et assertion du résultat
    dashboard_element = driver.find_element(By.ID, "dashboard-screen")
    classes = dashboard_element.get_attribute("class")
    avatar_present = len(driver.find_elements(By.ID, "user-avatar")) > 0
    
    assert "active" in classes or avatar_present, (
        "Erreur : L'utilisateur n'est pas redirigé vers son tableau de bord, "
        "ou l'avatar n'est pas présent en bas à gauche de la page."
    )
