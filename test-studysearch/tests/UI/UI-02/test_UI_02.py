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

def test_toggle_sidebar_ouvrir(driver):
    """
    [ UI-02 ] - Toggle de la Sidebar (Ouvrir) :
    Valide que le clic sur le menu burger (☰) restaure la visibilité de la barre latérale,
    masque le bouton burger et décale à nouveau la zone de contenu vers la droite.
    """
    base_url = "http://localhost:5000/"
    
    # ── Prérequis : Garantir l'existence de l'utilisateur de test en base
    db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = ?", (EMAIL_TEST.lower(),))
        conn.commit()
        
    res_creation = creer_utilisateur(EMAIL_TEST, PASSWORD_TEST, "Adam Ramzi", "127.0.0.1")
    assert res_creation["succes"]
    res_validation = valider_email(EMAIL_TEST, res_creation["code_verification"])
    assert res_validation["succes"]

    # ── Prérequis : Connexion de l'utilisateur et accès au Dashboard
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
    
    # ── Préparation de l'état du test : Fermer d'abord la sidebar pour tester sa réouverture
    # La sidebar étant ouverte par défaut, on clique sur le bouton de fermeture (◂) pour initier l'état "fermé"
    btn_toggle_sidebar = wait.until(EC.element_to_be_clickable((By.ID, "btn-toggle-sidebar")))
    btn_toggle_sidebar.click()
    
    # Attendre que la sidebar acquière la classe .collapsed et que le menu burger devienne visible
    sidebar = driver.find_element(By.CLASS_NAME, "sidebar")
    btn_open_sidebar = driver.find_element(By.ID, "btn-open-sidebar")
    wait.until(lambda d: "collapsed" in sidebar.get_attribute("class") and btn_open_sidebar.is_displayed())
    
    # Temporisation supplémentaire pour s'assurer que les transitions de largeur CSS sont stabilisées
    time.sleep(0.3)

    # ── Étape 1 : Localiser le bouton du menu burger (☰, ID: #btn-open-sidebar)
    # (Déjà localisé dans l'étape de préparation de l'état, nous vérifions qu'il est cliquable)
    wait.until(EC.element_to_be_clickable((By.ID, "btn-open-sidebar")))

    # ── Étape 2 : Cliquer sur ce menu burger
    btn_open_sidebar.click()
    
    # Attendre la fin de l'animation CSS (stabilisation des transitions)
    time.sleep(0.3)

    # ── Étape 3 (Assertion de la Sidebar) : Vérifier que la sidebar réapparaît (perd la classe .collapsed)
    assert "collapsed" not in sidebar.get_attribute("class"), "Erreur : La classe 'collapsed' est toujours présente sur la barre latérale après clic sur le burger."

    # ── Étape 4 (Assertion du Bouton Burger) : Vérifier que le menu burger disparaît proprement de l'interface
    assert not btn_open_sidebar.is_displayed(), "Erreur : Le menu burger est toujours visible après réouverture de la barre latérale."

    # ── Étape 5 (Assertion du Chat) : Vérifier que le conteneur principal se décale à nouveau vers la droite (margin-left restauré)
    main_content = driver.find_element(By.CLASS_NAME, "main-content")
    margin_left = main_content.value_of_css_property("margin-left")
    print(f"Marge de gauche du contenu principal après réouverture : {margin_left}")
    
    # La largeur par défaut étant de 280px en mode desktop
    assert margin_left == "280px", f"Erreur : La marge gauche est de '{margin_left}' au lieu de la valeur attendue '280px'."
