import os
from groq import Groq

def generer_reponse_chat(question, contexte, mode):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    if mode == "resume":
        system_prompt = "Tu es un assistant pédagogique. À partir du contexte fourni, génère un résumé clair et structuré en français avec des titres et des points clés. Réponds toujours en français."
    else: # mode == "extrait"
        system_prompt = "Tu es un assistant de recherche. Réponds précisément à la question en te basant uniquement sur le contexte fourni. Cite les passages exacts qui répondent à la question. Réponds toujours en français."
        
    user_prompt = f"Contexte:\n{contexte}\n\nQuestion: {question}"
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
        model="llama3-8b-8192",
    )
    
    return chat_completion.choices[0].message.content
