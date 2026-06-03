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
    
    # Résolution dynamique du chemin absolu de chromedriver.exe (4 niveaux car dans tests/Chat/CHAT-05/test_CHAT_05.py)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    chromedriver_path = os.path.join(base_dir, "chromedriver.exe")
    
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_persistance_des_onglets(driver):
    """
    [ CHAT-05 ] - Persistance des onglets :
    Vérifie que la sélection du document actif et l'historique des messages
    sont correctement restaurés lorsqu'on navigue entre différentes conversations dans la sidebar.
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

    # Injection JS pour simuler proprement deux conversations prêtes dans la sidebar
    driver.execute_script("""
        // Définir les documents disponibles
        allUserDocuments = [
            { nom_fichier: 'doc_a.pdf', type_fichier: 'PDF' },
            { nom_fichier: 'doc_b.pdf', type_fichier: 'PDF' }
        ];

        // Créer les deux conversations A et B
        conversations = [
            {
                id: 'conv_a',
                email: localStorage.getItem('email'),
                nom: 'Conversation A',
                messages: [{ role: 'user', content: 'Message A' }],
                documents: ['doc_a.pdf'],
                pdf_name: 'doc_a.pdf'
            },
            {
                id: 'conv_b',
                email: localStorage.getItem('email'),
                nom: 'Conversation B',
                messages: [{ role: 'user', content: 'Message B' }],
                documents: ['doc_b.pdf'],
                pdf_name: 'doc_b.pdf'
            }
        ];

        // Sauvegarder dans le localStorage
        localStorage.setItem('conversations', JSON.stringify(conversations));
        localStorage.setItem('studysearch_convos', JSON.stringify(conversations));

        // Mettre à jour l'affichage de la sidebar
        renderConversations();
    """)

    # ── Étape 1 : Cliquer sur l'onglet de la Conversation A dans la sidebar
    tab_a = wait.until(EC.element_to_be_clickable((
        By.XPATH, "//div[@id='history-content']//div[contains(@class, 'doc-card')][.//h4[contains(., 'Conversation A')]]"
    )))
    tab_a.click()

    # ── Étape 2 (Assertion) : Vérifier que le panneau central affiche "Message A" et que le sélecteur indique "doc_a.pdf"
    wait.until(EC.text_to_be_present_in_element((By.CLASS_NAME, "msg-user"), "Message A"))
    user_msg_el = driver.find_element(By.CLASS_NAME, "msg-user")
    assert "Message A" in user_msg_el.text, f"Erreur : Le chat n'affiche pas le bon message pour la Conversation A. Reçu : '{user_msg_el.text}'"
    
    select_pdf = driver.find_element(By.ID, "chat-pdf-select")
    assert select_pdf.get_attribute("value") == "doc_a.pdf", \
        f"Erreur : Le document sélectionné est incorrect pour la Conversation A : '{select_pdf.get_attribute('value')}'"

    # ── Étape 3 : Cliquer sur l'onglet de la Conversation B dans la sidebar
    tab_b = wait.until(EC.element_to_be_clickable((
        By.XPATH, "//div[@id='history-content']//div[contains(@class, 'doc-card')][.//h4[contains(., 'Conversation B')]]"
    )))
    tab_b.click()

    # ── Étape 4 (Assertion) : Vérifier que le chat affiche "Message B" et le sélecteur affiche "doc_b.pdf"
    wait.until(EC.text_to_be_present_in_element((By.CLASS_NAME, "msg-user"), "Message B"))
    user_msg_el = driver.find_element(By.CLASS_NAME, "msg-user")
    assert "Message B" in user_msg_el.text, f"Erreur : Le chat n'affiche pas le bon message pour la Conversation B. Reçu : '{user_msg_el.text}'"
    
    assert select_pdf.get_attribute("value") == "doc_b.pdf", \
        f"Erreur : Le document sélectionné est incorrect pour la Conversation B : '{select_pdf.get_attribute('value')}'"
