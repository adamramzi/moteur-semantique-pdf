import requests
import json

BASE_URL = "https://moteur-semantique-pdf.vercel.app"

def test_flow():
    print("1. Logging in as test@exemple.com...")
    login_url = f"{BASE_URL}/api/auth/login"
    payload = {
        "email": "test@exemple.com",
        "password": "monMotDePasse123"
    }
    
    res = requests.post(login_url, json=payload)
    print("Status:", res.status_code)
    print("Response:", res.text)
    if res.status_code != 200:
        print("Login failed!")
        return
        
    data = res.json()
    token = data["token"]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n2. Checking stats...")
    stats_res = requests.get(f"{BASE_URL}/api/stats", headers=headers)
    print("Stats Status:", stats_res.status_code)
    print("Stats Response:", stats_res.text)
    
    # If no documents are indexed, let's upload one
    stats = stats_res.json()
    if stats.get("nb_pdfs", 0) == 0:
        print("\n3. No documents found, uploading a test file...")
        files = {
            "files": ("test.txt", "Ce document contient des informations sur le projet StudySearch. Le projet est un assistant intelligent pour reviser.")
        }
        # For upload, header shouldn't specify content type json
        upload_headers = {
            "Authorization": f"Bearer {token}"
        }
        upload_res = requests.post(f"{BASE_URL}/api/upload", headers=upload_headers, files=files)
        print("Upload Status:", upload_res.status_code)
        print("Upload Response:", upload_res.text)
        
    print("\n4. Testing /api/chat...")
    chat_payload = {
        "query": "C'est quoi StudySearch ?",
        "mode": "recherche"
    }
    chat_res = requests.post(f"{BASE_URL}/api/chat", headers=headers, json=chat_payload)
    print("Chat Status:", chat_res.status_code)
    print("Chat Response:", chat_res.text)

if __name__ == "__main__":
    test_flow()
