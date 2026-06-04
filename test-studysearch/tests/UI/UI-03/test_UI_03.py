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

def test_bascule_theme(driver):
    """
    [ UI-03 ] - Bascule Thème Clair/Sombre :
    Valide que le changement de thème vers le mode clair applique instantanément la classe
    'light-mode' sur la balise body, et que ce thème persiste après un rafraîchissement (F5).
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

    # ── Prérequis : Connexion de l'utilisateur
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
    
    # Vérifier l'état initial : s'assurer que la balise <body> ne possède pas la classe .light-mode (sombre par défaut)
    body = driver.find_element(By.TAG_NAME, "body")
    classes_initiales = body.get_attribute("class") or ""
    assert "light-mode" not in classes_initiales, "Erreur : L'application est déjà en thème clair au démarrage."

    # ── Étape 1 : Localiser et cliquer sur le bouton d'engrenage des paramètres (⚙️)
    settings_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-logout-icon")))
    settings_btn.click()

    # ── Étape 2 : Attendre que la modale #settings-modal soit visible
    def check_modal_visible(d):
        try:
            modal = d.find_element(By.ID, "settings-modal")
            return "hidden" not in modal.get_attribute("class") and modal.is_displayed()
        except Exception:
            return False
    wait.until(check_modal_visible)

    # ── Étape 3 : Localiser le bouton "Basculer Thème (Clair/Sombre)" dans la modale et cliquer dessus
    theme_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[onclick='toggleTheme()']")))
    theme_btn.click()

    # ── Étape 4 (Assertion DOM instantanée) : Vérifier que la balise <body> a immédiatement acquis la classe .light-mode
    body = driver.find_element(By.TAG_NAME, "body")
    wait.until(lambda d: "light-mode" in (d.find_element(By.TAG_NAME, "body").get_attribute("class") or ""))
    assert "light-mode" in (body.get_attribute("class") or ""), "Erreur : La classe 'light-mode' n'a pas été ajoutée au body après clic."

    # ── Étape 5 (Vérification de la persistance) : Rafraîchir brutalement la page en utilisant driver.refresh()
    driver.refresh()

    # ── Étape 6 (Assertion après F5) : Attendre le rechargement de la page et vérifier la persistance
    # Le rafraîchissement va recharger le JS, qui lit le localStorage. 
    # Attendre que la balise body possède à nouveau la classe light-mode.
    wait.until(lambda d: "light-mode" in (d.find_element(By.TAG_NAME, "body").get_attribute("class") or ""))
    body_apres_refresh = driver.find_element(By.TAG_NAME, "body")
    assert "light-mode" in (body_apres_refresh.get_attribute("class") or ""), "Erreur : La classe 'light-mode' n'a pas persisté après rafraîchissement F5 de la page."

    # ── Étape 7 (Assertion LocalStorage) : Vérifier la clé 'theme' stockée
    theme_local_storage = driver.execute_script("return localStorage.getItem('theme');")
    print(f"Thème sauvegardé dans localStorage : '{theme_local_storage}'")
    assert theme_local_storage == "light", f"Erreur : La clé 'theme' dans le localStorage vaut '{theme_local_storage}' au lieu de 'light'."
