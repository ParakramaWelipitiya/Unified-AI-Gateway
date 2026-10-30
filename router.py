import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Define your fallback order. 
# Groq is first (fastest), DeepSeek second, Gemini third.
PROVIDERS = [
    {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": os.getenv("GROQ_API_KEY"),
        "model": "llama3-70b-8192"
    },
    {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com/chat/completions",
        "key": os.getenv("DEEPSEEK_API_KEY"),
        "model": "deepseek-chat"
    },
    {
        "name": "Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key": os.getenv("GEMINI_API_KEY"),
        "model": "gemini-1.5-pro"
    }
]

def chat_with_fallback(messages):
    for provider in PROVIDERS:
        if not provider["key"]:
            continue  # Skip if you haven't added this key yet

        headers = {
            "Authorization": f"Bearer {provider['key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": provider["model"],
            "messages": messages,
            "temperature": 0.7
        }

        try:
            response = requests.post(provider["url"], headers=headers, json=payload)
            
            # If rate limit hit (429), catch it and loop to the next provider
            if response.status_code == 429:
                print(f"[-] {provider['name']} limit reached. Falling back...")
                continue
                
            # If successful, return the text and the provider used
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"], provider['name']
            
        except requests.exceptions.RequestException:
            print(f"[!] Network error with {provider['name']}. Trying next...")
            continue
            
    return "Error: All AI providers are rate-limited or unavailable.", "None"