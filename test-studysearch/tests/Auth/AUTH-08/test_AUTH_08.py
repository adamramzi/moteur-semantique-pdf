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

def test_modification_mot_de_passe(driver):
    """
    [ AUTH-08 ] - Modification du mot de passe :
    Vérifie la mise à jour réussie du mot de passe avec déconnexion forcée par sécurité.
    """
    base_url = "http://localhost:5000/"
    timestamp = int(time.time())
    email_unique = f"password_test_{timestamp}@test.local"
    ancien_mdp = "AncienPass123!"
    nouveau_mdp = "NouveauPass456!"
    
    # ── Prérequis : Créer un compte utilisateur jetable et se connecter
    driver.get(base_url)
    wait = WebDriverWait(driver, 10)
    
    # Passer l'écran de bienvenue si présent
    try:
        start_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-home-start")))
        start_btn.click()
    except Exception:
        pass
        
    # Aller sur le formulaire d'inscription
    go_register_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-go-register")))
    go_register_btn.click()
    
    # Remplir le formulaire
    wait.until(EC.visibility_of_element_located((By.ID, "register-fullname"))).send_keys("Utilisateur Jetable")
    driver.find_element(By.ID, "reg-email").send_keys(email_unique)
    driver.find_element(By.ID, "reg-password").send_keys(ancien_mdp)
    driver.find_element(By.ID, "reg-password2").send_keys(ancien_mdp)
    driver.find_element(By.ID, "btn-register").click()
    
    # Validation éventuelle par code
    try:
        # Attendre que l'écran de vérification s'affiche
        WebDriverWait(driver, 5).until(
            lambda d: d.find_element(By.ID, "verify-screen").is_displayed() or 
                      "active" in d.find_element(By.ID, "dashboard-screen").get_attribute("class")
        )
        
        if driver.find_element(By.ID, "verify-screen").is_displayed():
            time.sleep(1.5)  # Laisser le temps de l'écriture en base
            
            db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
            code_verification = None
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT code_verification FROM users WHERE email = ?", (email_unique.lower(),))
                row = cursor.fetchone()
                if row:
                    code_verification = row[0]
            
            if code_verification:
                driver.find_element(By.ID, "verify-code").send_keys(str(code_verification))
                driver.find_element(By.ID, "btn-verify").click()
                
                # Attendre l'écran de connexion et se connecter
                wait.until(EC.visibility_of_element_located((By.ID, "login-form")))
                driver.find_element(By.ID, "login-email").send_keys(email_unique)
                driver.find_element(By.ID, "login-password").send_keys(ancien_mdp)
                driver.find_element(By.ID, "btn-login").click()
    except Exception as e:
        print(f"[Info] Étape de vérification ignorée ou automatique : {e}")

    # S'assurer que le compte est sur le Dashboard
    wait.until(lambda d: "active" in d.find_element(By.ID, "dashboard-screen").get_attribute("class"))

    # Nettoyer les toasts existants
    driver.execute_script("document.getElementById('toast-container').innerHTML = '';")

    # ── Étape 1 : Ouvrir la modale paramètres (⚙️)
    btn_settings = wait.until(EC.element_to_be_clickable((By.ID, "btn-logout-icon")))
    btn_settings.click()
    
    # S'assurer que la modale est visible
    wait.until(lambda d: not d.find_element(By.ID, "settings-modal").get_attribute("class").count("hidden"))

    # ── Étape 2 & 3 : Localiser et remplir les champs de modification de mot de passe
    input_old = wait.until(EC.visibility_of_element_located((By.ID, "settings-old-password")))
    input_new = driver.find_element(By.ID, "settings-new-password")
    input_confirm = driver.find_element(By.ID, "settings-confirm-password")

    input_old.send_keys(ancien_mdp)
    input_new.send_keys(nouveau_mdp)
    input_confirm.send_keys(nouveau_mdp)

    # ── Étape 4 : Cliquer sur le bouton de validation du changement
    btn_submit = driver.find_element(By.ID, "btn-settings-change-password")
    btn_submit.click()

    # ── Étape 5 (Assertion Toast) : Attendre le toast de succès
    toast_success = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "toast-success")))
    assert toast_success.is_displayed(), "Erreur : Aucun Toast de succès affiché pour confirmer le changement."

    # ── Étape 6 (Assertion Déconnexion forcée)
    # 1. La modale doit se fermer (contenir la classe hidden)
    wait.until(lambda d: "hidden" in d.find_element(By.ID, "settings-modal").get_attribute("class"))
    
    # 2. Redirection vers l'écran d'accueil/connexion (#home-screen doit avoir la classe active)
    wait.until(lambda d: "active" in d.find_element(By.ID, "home-screen").get_attribute("class"))
    
    # 3. Purge du localStorage (le token doit être supprimé)
    token = driver.execute_script("return localStorage.getItem('token');")
    assert token is None or token == "", "Erreur : Le token de session n'a pas été supprimé du localStorage."
