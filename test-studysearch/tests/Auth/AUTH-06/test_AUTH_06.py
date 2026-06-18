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

# Configuration de l'utilisateur de test
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
    # chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_annulation_suppression_compte(driver):
    """
    [ AUTH-06 ] - Annulation de la suppression du compte :
    Vérifie que lorsqu'un utilisateur clique sur "Supprimer mon compte" mais refuse
    la boîte de dialogue de confirmation, son compte n'est pas supprimé et sa session
    reste parfaitement active.
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
    
    # Attendre d'être sur le Dashboard
    wait.until(lambda d: "active" in d.find_element(By.ID, "dashboard-screen").get_attribute("class"))

    # ── Étape 1 : Cliquer sur le bouton des paramètres (⚙️) et attendre l'ouverture de #settings-modal
    settings_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-logout-icon")))
    settings_btn.click()
    
    # Attendre que la modale devienne visible (qu'elle ne contienne plus la classe hidden)
    def check_modal_visible(d):
        try:
            modal = d.find_element(By.ID, "settings-modal")
            classes = modal.get_attribute("class")
            return "hidden" not in classes and modal.is_displayed()
        except Exception:
            return False
    wait.until(check_modal_visible)

    # ── Étape 2 : Trouver le bouton "Supprimer mon compte" et cliquer dessus
    # On utilise le sélecteur d'attribut pour le bouton exécutant deleteAccount()
    delete_account_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[onclick='deleteAccount()']")))
    delete_account_btn.click()

    # ── Étape 3 : Attendre l'apparition de la boîte de dialogue de confirmation native du navigateur (confirm())
    wait.until(EC.alert_is_present())

    # ── Étape 4 : Basculer sur l'alerte et l'annuler (dismiss)
    alert = driver.switch_to.alert
    print(f"Texte de l'alerte intercepté : '{alert.text}'")
    alert.dismiss()

    # ── Étape 5 (Assertion) : Vérifier que l'utilisateur n'a pas été déconnecté (le Dashboard reste actif) et que la modale reste ouverte
    dashboard_element = driver.find_element(By.ID, "dashboard-screen")
    modal_element = driver.find_element(By.ID, "settings-modal")
    
    # Le dashboard doit être toujours actif
    assert "active" in dashboard_element.get_attribute("class"), "Erreur : L'utilisateur a été déconnecté ou redirigé à tort alors qu'il a annulé la suppression."
    
    # La modale de réglages doit toujours être présente et visible
    assert "hidden" not in modal_element.get_attribute("class"), "Erreur : La modale des paramètres s'est fermée de manière inattendue suite à l'annulation."
    
    # Le localStorage doit toujours contenir les informations de session
    local_storage_token = driver.execute_script("return localStorage.getItem('token');")
    assert local_storage_token is not None and len(local_storage_token) > 0, "Erreur : Le token de session a été effacé du localStorage suite à l'annulation."
    
    print("Succès : L'annulation de la suppression du compte s'est comportée de manière conforme.")
