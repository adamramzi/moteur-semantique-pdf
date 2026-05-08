from sentence_transformers import SentenceTransformer

def main():
    # Charge le modèle all-MiniLM-L6-v2
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Encode deux phrases : "Bonjour le monde" et "Hello world"
    phrases = ["Bonjour le monde", "Hello world"]
    embeddings = model.encode(phrases)
    
    # Affiche la shape des embeddings
    print(f"✅ Succès ! Shape: {embeddings.shape}")

if __name__ == "__main__":
    main()
