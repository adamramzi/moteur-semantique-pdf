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
from fpdf import FPDF

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
    # chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_upload_document_valide(driver, dummy_pdf):
    """
    [ DOC-01 ] - Upload de document valide :
    Vérifie qu'un utilisateur connecté peut uploader un fichier PDF valide,
    qu'un toast de succès est affiché et que le document apparaît dans le sélecteur.
    """
    base_url = "http://localhost:5000/"
    
    # ── Prérequis : Garantir l'existence de l'utilisateur en base et nettoyer ses anciens documents/recherches
    db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE user_id = (SELECT id FROM users WHERE email = ?)", (EMAIL_TEST.lower(),))
        cursor.execute("DELETE FROM user_indices WHERE user_id = (SELECT id FROM users WHERE email = ?)", (EMAIL_TEST.lower(),))
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

    # ── Étape 1 : Localiser le champ d'upload caché
    file_input = driver.find_element(By.ID, "file-input")

    # ── Étape 2 : Envoyer le chemin absolu du fichier PDF généré sur cet input
    file_input.send_keys(dummy_pdf)

    # Vider le conteneur de toast pour éviter que le toast "Connexion réussie !" ne fausse les assertions d'upload
    driver.execute_script("document.getElementById('toast-container').innerHTML = '';")

    # ── Étape 3 : Cliquer sur le bouton d'upload ("Analyser et enregistrer")
    # Attendre que le conteneur du bouton d'upload apparaisse
    wait.until(EC.visibility_of_element_located((By.ID, "upload-btn-container")))
    btn_upload = wait.until(EC.element_to_be_clickable((By.ID, "btn-upload")))
    btn_upload.click()

    # ── Étape 4 (Assertion Loader/Toast) : Vérifier l'apparition de l'indicateur de chargement
    loading_overlay = driver.find_element(By.ID, "loading-overlay")
    wait.until(lambda d: "active" in loading_overlay.get_attribute("class") or not loading_overlay.is_displayed())
    
    # Attendre la fin du chargement et le toast de succès
    toast_success = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "toast-success")))
    assert toast_success.is_displayed(), "Erreur : Le toast de succès de l'upload n'est pas affiché."
    assert "succès" in toast_success.text.lower() or "analysé" in toast_success.text.lower() or "enregistré" in toast_success.text.lower(), \
        f"Erreur : Le texte du toast de succès est inattendu : '{toast_success.text}'"

    # ── Étape 5 (Assertion UI) : Vérifier le dropdown
    select_pdf = wait.until(EC.presence_of_element_located((By.ID, "chat-pdf-select")))
    # Attendre que le sélecteur soit activé
    wait.until(lambda d: d.find_element(By.ID, "chat-pdf-select").is_enabled())
    
    # Vérifier que "dummy_document.pdf" est bien présent dans la liste des options
    options = select_pdf.find_elements(By.TAG_NAME, "option")
    option_values = [opt.get_attribute("value") for opt in options]
    assert "dummy_document.pdf" in option_values, f"Erreur : Le fichier 'dummy_document.pdf' n'apparaît pas dans la liste des options. Options trouvées : {option_values}"
