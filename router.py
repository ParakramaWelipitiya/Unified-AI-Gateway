import os
import requests
from dotenv import load_dotenv

load_dotenv()

PROVIDERS = [
    {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": os.getenv("GROQ_API_KEY"),
        "model": "openai/gpt-oss-120b"
    },
    {
        "name": "Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key": os.getenv("GEMINI_API_KEY"),
        "model": "gemini-3.8-flash"
    }
]

# Helper function to let the UI know what models are available
def get_available_providers():
    return [p["name"] for p in PROVIDERS if p["key"]]

def chat_with_fallback(messages, preferred_provider=None):
    providers_to_try = PROVIDERS.copy()
    
    # If the user typed /switch and picked a model, move it to the front of the list
    if preferred_provider:
        for i, p in enumerate(providers_to_try):
            if p["name"].lower() == preferred_provider.lower():
                providers_to_try.insert(0, providers_to_try.pop(i))
                break

    for provider in providers_to_try:
        if not provider["key"]:
            continue

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
            
            if response.status_code == 429:
                print(f"[-] {provider['name']} limit reached. Falling back...")
                continue
                
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"], provider['name']
            
            print(f"[!] {provider['name']} failed (Status {response.status_code}): {response.text}")
            
        except requests.exceptions.RequestException:
            print(f"[!] Network error with {provider['name']}. Trying next...")
            continue
            
    return "Error: All AI providers are rate-limited or unavailable.", "None"