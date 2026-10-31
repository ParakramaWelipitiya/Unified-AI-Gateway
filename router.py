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

# Translate HTTP status codes into plain English
ERROR_MAP = {
    400: "Invalid Request or API Key format.",
    401: "Unauthorized - Your API Key is invalid or missing.",
    402: "Insufficient Balance - Your free credits have run out.",
    403: "Forbidden - API key restricted or blocked.",
    404: "Not Found - The model name or endpoint URL is incorrect.",
    429: "Rate Limit Exceeded - Too many requests.",
    500: "Internal Server Error - The AI provider's server crashed.",
    502: "Bad Gateway - The AI provider is down.",
    503: "Service Unavailable - The AI provider's servers are overloaded.",
    504: "Gateway Timeout - The AI provider took too long to respond."
}

def get_available_providers():
    return [p["name"] for p in PROVIDERS if p["key"]]

def chat_with_fallback(messages, preferred_provider=None):
    providers_to_try = PROVIDERS.copy()
    
    # Prioritize selected model if /switch was used
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
            
            # Silent fallbacks for temporary traffic issues (Overloads, Rate Limits)
            if response.status_code in [429, 502, 503, 504]:
                print(f"[-] {provider['name']} is busy or rate-limited. Falling back...")
                continue
                
            # Success
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"], provider['name']
            
            # Hard Errors (Invalid Keys, Wrong Models, etc.)
            friendly_msg = ERROR_MAP.get(response.status_code, "Unknown Error occurred.")
            print(f"\n[!] {provider['name']} Error: {friendly_msg}")
            
            # Interactive prompt for the raw error
            show_raw = input(f"    Wanna see the full {provider['name']} error? (y/n): ")
            if show_raw.lower() in ['y', 'yes']:
                print(f"    Raw JSON (Status {response.status_code}): {response.text}\n")
            
            print(f"[-] Moving to the next available model...\n")
            
        except requests.exceptions.RequestException:
            print(f"\n[!] Network error connecting to {provider['name']}. Trying next...")
            continue
            
    return "Error: All AI providers are rate-limited, invalid, or unavailable.", "None"