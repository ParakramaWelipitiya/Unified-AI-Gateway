import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Translate HTTP status codes into plain English
ERROR_MAP = {
    400: "Invalid Request or API Key format.",
    401: "Unauthorized - Your API Key is invalid or missing.",
    402: "Insufficient Balance - Your free credits have run out.",
    403: "Forbidden - API key restricted or blocked.",
    404: "Not Found - The model name is deprecated or endpoint is invalid.",
    429: "Rate Limit Exceeded - Too many requests or quota reached.",
    500: "Internal Server Error - Google servers encountered an issue.",
    502: "Bad Gateway - The AI provider is temporarily unavailable.",
    503: "Service Unavailable - Google AI servers are overloaded.",
    504: "Gateway Timeout - The AI provider took too long to respond."
}

# Default known Gemini/Google models to fallback on if API listing fails
DEFAULT_GEMINI_MODELS = [
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
    "gemini-pro-latest",
    "gemini-3.8-flash"
]

_CACHED_GEMINI_MODELS = []

def fetch_google_models(force_refresh=False):
    """
    Fetches available models dynamically from Google AI Studio using the Gemini API.
    Filters for models that support generateContent and prioritizes active chat models.
    """
    global _CACHED_GEMINI_MODELS
    if _CACHED_GEMINI_MODELS and not force_refresh:
        return _CACHED_GEMINI_MODELS

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return DEFAULT_GEMINI_MODELS

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = []
            for item in data.get("models", []):
                methods = item.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    name = item.get("name", "").replace("models/", "")
                    # Filter out non-text/specialized endpoints (TTS, image generation, robotics, etc.)
                    if not any(skip in name.lower() for skip in [
                        "tts", "image", "banana", "robotics", "computer-use", "clip", "transcribe", "rerouted"
                    ]):
                        models.append(name)

            if models:
                # Prioritize high-availability active chat models
                priority_order = [
                    "gemini-flash-latest",
                    "gemini-3.5-flash",
                    "gemini-3.1-flash-lite",
                    "gemma-4-26b-a4b-it",
                    "gemma-4-31b-it",
                    "gemini-pro-latest",
                    "gemini-3.8-flash"
                ]
                sorted_models = []
                for p in priority_order:
                    if p in models:
                        sorted_models.append(p)
                        models.remove(p)
                sorted_models.extend(models)
                _CACHED_GEMINI_MODELS = sorted_models
                return _CACHED_GEMINI_MODELS
        else:
            print(f"[!] Warning: Failed to fetch models from Google (HTTP {response.status_code}). Using default list.")
    except Exception as e:
        print(f"[!] Warning: Could not reach Google to update model list ({e}). Using default list.")

    _CACHED_GEMINI_MODELS = DEFAULT_GEMINI_MODELS
    return _CACHED_GEMINI_MODELS

def call_google_gemini(model_name, messages, api_key, temperature=0.7, timeout=15):
    """
    Calls Google AI Studio Generative Language API using native generateContent format.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    contents = []
    system_instruction = None

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
        else:
            contents.append({"role": "user", "parts": [{"text": content}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature
        }
    }
    if system_instruction:
        payload["systemInstruction"] = system_instruction

    return requests.post(url, headers=headers, json=payload, timeout=timeout)

def call_openai_compatible(url, key, model, messages, temperature=0.7, timeout=15):
    """
    Calls OpenAI-compatible endpoints (e.g. Groq, DeepSeek).
    """
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    return requests.post(url, headers=headers, json=payload, timeout=timeout)

def get_configured_providers():
    """
    Returns list of active providers that have valid API keys.
    """
    providers = []
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    if gemini_key:
        providers.append("Gemini")
    if groq_key:
        providers.append("Groq")
    if deepseek_key:
        providers.append("DeepSeek")
    return providers

def get_available_selection_options():
    """
    Returns high-level options for the /switch menu:
    Providers and available Gemini models from Google.
    """
    options = []
    if os.getenv("GEMINI_API_KEY"):
        options.append("Gemini (Auto-switch models)")
        models = fetch_google_models()
        for m in models[:8]:  # Show top 8 available Gemini models
            options.append(f"Gemini: {m}")
    if os.getenv("GROQ_API_KEY"):
        options.append("Groq (llama-3.3-70b-versatile)")
    if os.getenv("DEEPSEEK_API_KEY"):
        options.append("DeepSeek (deepseek-chat)")
    return options

def chat_with_fallback(messages, preferred_selection=None):
    """
    Routes chat completion with automatic failover:
    - If preferred_selection is specified, attempts it first.
    - If Gemini is used, automatically switches through Google models on 429/5xx/404/timeout.
    - Falls back to secondary providers if configured.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    gemini_models = fetch_google_models()

    # Determine execution order based on preferred_selection
    preferred_gemini_model = None
    target_provider = None

    if preferred_selection:
        pref = preferred_selection.lower().strip()
        if pref.startswith("gemini:"):
            target_provider = "gemini"
            preferred_gemini_model = preferred_selection.split(":", 1)[1].strip()
        elif "gemini" in pref:
            target_provider = "gemini"
        elif "groq" in pref:
            target_provider = "groq"
        elif "deepseek" in pref:
            target_provider = "deepseek"

    # Sequence of providers to attempt
    provider_order = []
    if target_provider:
        provider_order.append(target_provider)
    for p in ["gemini", "groq", "deepseek"]:
        if p not in provider_order:
            provider_order.append(p)

    for provider in provider_order:
        if provider == "gemini":
            if not gemini_key:
                continue

            models_to_try = list(gemini_models)
            if preferred_gemini_model:
                if preferred_gemini_model in models_to_try:
                    models_to_try.remove(preferred_gemini_model)
                models_to_try.insert(0, preferred_gemini_model)

            for g_model in models_to_try:
                try:
                    resp = call_google_gemini(g_model, messages, gemini_key, timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts and "text" in parts[0]:
                                return parts[0]["text"], f"Google AI Studio ({g_model})"
                            reason = candidates[0].get("finishReason", "UNKNOWN")
                            return f"[Response completed with reason: {reason}]", f"Google AI Studio ({g_model})"
                        return "[No text generated in response]", f"Google AI Studio ({g_model})"

                    # Auto-switching conditions for Gemini models:
                    # 429: Rate limit, 404: Deprecated model, 500/502/503/504: Overload/crashed
                    if resp.status_code in [404, 429, 500, 502, 503, 504]:
                        reason = ERROR_MAP.get(resp.status_code, f"HTTP {resp.status_code}")
                        print(f"[-] Gemini model '{g_model}' ({reason}). Auto-switching to next model...")
                        continue

                    # Hard error (e.g. 400 or 403)
                    friendly_msg = ERROR_MAP.get(resp.status_code, f"HTTP {resp.status_code}")
                    print(f"\n[!] Gemini Error ({friendly_msg}): {resp.text}")
                    break

                except requests.exceptions.Timeout:
                    print(f"[-] Gemini model '{g_model}' timed out. Auto-switching to next model...")
                    continue
                except requests.exceptions.RequestException as e:
                    print(f"[-] Network error connecting to Gemini ({g_model}): {e}. Trying next...")
                    continue

        elif provider == "groq":
            if not groq_key:
                continue
            groq_url = "https://api.groq.com/openai/v1/chat/completions"
            groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
            for q_model in groq_models:
                try:
                    resp = call_openai_compatible(groq_url, groq_key, q_model, messages, timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"], f"Groq ({q_model})"
                    if resp.status_code in [429, 502, 503, 504]:
                        print(f"[-] Groq ({q_model}) busy or rate-limited. Falling back...")
                        continue
                    friendly_msg = ERROR_MAP.get(resp.status_code, f"HTTP {resp.status_code}")
                    print(f"\n[!] Groq Error: {friendly_msg}")
                    break
                except requests.exceptions.RequestException:
                    print(f"\n[!] Network error connecting to Groq ({q_model}). Trying next...")
                    continue

        elif provider == "deepseek":
            if not deepseek_key:
                continue
            ds_url = "https://api.deepseek.com/chat/completions"
            try:
                resp = call_openai_compatible(ds_url, deepseek_key, "deepseek-chat", messages, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"], "DeepSeek (deepseek-chat)"
                if resp.status_code in [429, 502, 503, 504]:
                    print(f"[-] DeepSeek busy or rate-limited. Falling back...")
                    continue
                friendly_msg = ERROR_MAP.get(resp.status_code, f"HTTP {resp.status_code}")
                print(f"\n[!] DeepSeek Error: {friendly_msg}")
            except requests.exceptions.RequestException:
                print(f"\n[!] Network error connecting to DeepSeek. Trying next...")
                continue

    return "Error: All AI providers and models are rate-limited, invalid, or unavailable.", "None"
