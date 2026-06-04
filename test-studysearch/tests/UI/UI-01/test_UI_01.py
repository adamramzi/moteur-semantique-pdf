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

def test_toggle_sidebar_fermer(driver):
    """
    [ UI-01 ] - Toggle de la Sidebar (Fermer) :
    Valide que le clic sur le bouton de réduction masque correctement la barre latérale,
    affiche le bouton d'ouverture (burger menu) et élargit la zone de contenu principal.
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
    
    # ── Étape 1 : Attendre que le tableau de bord soit actif et la barre latérale (Sidebar) visible par défaut
    wait.until(lambda d: "active" in d.find_element(By.ID, "dashboard-screen").get_attribute("class"))
    
    sidebar = driver.find_element(By.CLASS_NAME, "sidebar")
    main_content = driver.find_element(By.CLASS_NAME, "main-content")
    btn_open_sidebar = driver.find_element(By.ID, "btn-open-sidebar")
    
    # S'assurer que la sidebar est initialement ouverte (ne possède pas la classe collapsed)
    assert "collapsed" not in sidebar.get_attribute("class"), "Erreur : La barre latérale est déjà fermée au chargement."
    assert not btn_open_sidebar.is_displayed(), "Erreur : Le bouton d'ouverture est affiché alors que la barre latérale est ouverte."

    # ── Étape 2 : Localiser le bouton de fermeture de la barre latérale (ID : #btn-toggle-sidebar)
    btn_toggle_sidebar = wait.until(EC.element_to_be_clickable((By.ID, "btn-toggle-sidebar")))

    # ── Étape 3 : Cliquer sur ce bouton
    btn_toggle_sidebar.click()
    
    # Attendre dynamiquement que la transition CSS de la marge gauche soit terminée (qu'elle passe à 0px)
    wait.until(lambda d: d.find_element(By.CLASS_NAME, "main-content").value_of_css_property("margin-left") in ["0px", "0"])

    # ── Étape 4 (Assertion de la Sidebar) : Vérifier que la sidebar a bien la classe .collapsed
    assert "collapsed" in sidebar.get_attribute("class"), "Erreur : La classe 'collapsed' n'a pas été ajoutée à la barre latérale."

    # ── Étape 5 (Assertion du Bouton Burger) : Vérifier que le menu burger (#btn-open-sidebar) est devenu visible
    assert btn_open_sidebar.is_displayed(), "Erreur : Le menu burger pour réouvrir la barre latérale n'est pas affiché."

    # ── Étape 6 (Assertion du Chat) : Vérifier que le conteneur principal du chat occupe désormais toute la largeur (margin-left à 0px)
    margin_left = main_content.value_of_css_property("margin-left")
    print(f"Marge de gauche du contenu principal après fermeture : {margin_left}")
    
    # En CSS, marginLeft = 0 ou 0px signifie que l'élément prend toute la largeur libre (sans décalage)
    assert margin_left in ["0px", "0"], f"Erreur : La marge gauche est de '{margin_left}' au lieu de '0px'."
