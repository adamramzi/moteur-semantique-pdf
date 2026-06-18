import os
import sys
import time
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ajout du chemin de l'application locale pour pouvoir interagir directement avec la base de données
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
    # chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_connexion_reussie(driver):
    """
    [ AUTH-02 ] - Connexion réussie :
    Crée un utilisateur valide en base de données, puis teste la connexion
    réussie à l'application StudySearch et l'accès au tableau de bord.
    """
    base_url = "http://localhost:5000/"
    
    # ── Étape 1 : Créer et valider un compte de test directement en base de données pour un test 100% autonome
    timestamp = int(time.time())
    email_unique = f"test_login_{timestamp}@studysearch.local"
    mot_de_passe = "MotDePasse123!"
    nom_complet = "Utilisateur Connexion"
    
    # Création de l'utilisateur
    res_creation = creer_utilisateur(email_unique, mot_de_passe, nom_complet, "127.0.0.1")
    assert res_creation["succes"], f"Échec de la création de l'utilisateur de test en base : {res_creation.get('erreur')}"
    
    # Validation de l'utilisateur (mise à jour de est_verifie à 1)
    res_validation = valider_email(email_unique, res_creation["code_verification"])
    assert res_validation["succes"], f"Échec de la validation de l'utilisateur de test : {res_validation.get('erreur')}"
    
    # ── Étape 2 : Charger http://localhost:5000/ et s'assurer que le formulaire de connexion est prêt
    driver.get(base_url)
    wait = WebDriverWait(driver, 10)
    
    # Attendre et cliquer sur le bouton d'accueil si l'écran de présentation d'accueil s'affiche
    try:
        start_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-home-start")))
        start_btn.click()
    except Exception:
        # Déjà sur l'écran de login
        pass
        
    # Attendre que le formulaire de connexion (#login-form) soit visible
    wait.until(EC.visibility_of_element_located((By.ID, "login-form")))
    
    # ── Étape 3 : Remplir le champ de l'adresse e-mail avec l'e-mail créé
    login_email_field = driver.find_element(By.ID, "login-email")
    login_email_field.send_keys(email_unique)
    
    # ── Étape 4 : Remplir le champ du mot de passe avec le mot de passe valide
    login_password_field = driver.find_element(By.ID, "login-password")
    login_password_field.send_keys(mot_de_passe)
    
    # ── Étape 5 : Cliquer sur le bouton de connexion (Se connecter)
    btn_login = driver.find_element(By.ID, "btn-login")
    btn_login.click()
    
    # ── Étape 6 (Assertion) : Attendre explicitement la connexion et vérifier que l'accès au tableau de bord a réussi
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
        
    # Attente de la redirection vers le tableau de bord
    wait.until(check_dashboard_or_avatar)
    
    # Récupération de l'état final pour valider l'assertion
    dashboard_element = driver.find_element(By.ID, "dashboard-screen")
    classes = dashboard_element.get_attribute("class")
    avatar_present = len(driver.find_elements(By.ID, "user-avatar")) > 0
    
    # Validation du succès du test
    assert "active" in classes or avatar_present, (
        "La connexion a échoué : l'écran de tableau de bord n'est pas actif "
        "et l'avatar utilisateur n'est pas affiché."
    )
