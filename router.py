import os
import requests
from dotenv import load_dotenv
from keys import get_keys, reload_env, mask_key

reload_env()

# Translate HTTP status codes into plain English
ERROR_MAP = {
    400: "Invalid Request or API Key format.",
    401: "Unauthorized - API Key is invalid or expired.",
    402: "Insufficient Balance - Free tier quota exhausted.",
    403: "Forbidden - API key restricted or quota blocked.",
    404: "Not Found - Model is deprecated, unavailable, or paid-only.",
    429: "Rate Limit Exceeded - Too many requests or quota reached.",
    500: "Internal Server Error - Provider servers encountered an issue.",
    502: "Bad Gateway - Provider is temporarily unreachable.",
    503: "Service Unavailable - Provider servers are overloaded.",
    504: "Gateway Timeout - Request took too long to complete."
}

# Reliable high-availability Gemini models
DEFAULT_GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-pro-latest",
    "gemini-3.8-flash"
]

# Top tested free models on OpenRouter
DEFAULT_OPENROUTER_FREE_MODELS = [
    "nvidia/nemotron-3.5-lightning:free",
    "liquid/lfm-2.5-2.6b:free",
    "thinkingmachines/inkling:free",
    "google/gemma-4-26b-a4b-it:free",
    "recursive/flint-v1.0:free",
    "xingchen-agi/xing4.0-29b-a4b:free",
    "cohere/north-mini-code:free"
]

_CACHED_GEMINI_MODELS = []
_CACHED_OPENROUTER_MODELS = []

def fetch_google_models(force_refresh=False):
    """
    Fetches available models dynamically from Google AI Studio.
    Filters for models that support generateContent and prioritizes stable chat models.
    """
    global _CACHED_GEMINI_MODELS
    if _CACHED_GEMINI_MODELS and not force_refresh:
        return _CACHED_GEMINI_MODELS

    keys = get_keys("gemini")
    if not keys:
        return DEFAULT_GEMINI_MODELS

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={keys[0]}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = []
            for item in data.get("models", []):
                methods = item.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    name = item.get("name", "").replace("models/", "")
                    if not any(skip in name.lower() for skip in [
                        "tts", "image", "banana", "robotics", "computer-use", "clip",
                        "transcribe", "rerouted", "gemma"
                    ]):
                        models.append(name)

            if models:
                priority_order = [
                    "gemini-3.5-flash",
                    "gemini-3.1-flash-lite",
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
    except Exception as e:
        print(f"[!] Warning: Could not reach Google to update model list ({e}). Using default list.")

    _CACHED_GEMINI_MODELS = DEFAULT_GEMINI_MODELS
    return _CACHED_GEMINI_MODELS

def fetch_openrouter_models(force_refresh=False):
    """
    Fetches live free models dynamically from OpenRouter.
    Identifies active models with :free or 0 pricing.
    """
    global _CACHED_OPENROUTER_MODELS
    if _CACHED_OPENROUTER_MODELS and not force_refresh:
        return _CACHED_OPENROUTER_MODELS

    try:
        r = requests.get("https://openrouter.ai/api/v1/models", timeout=8)
        if r.status_code == 200:
            free_models = []
            for m in r.json().get("data", []):
                mid = m.get("id", "")
                pricing = m.get("pricing", {})
                prompt_p = float(pricing.get("prompt", 0) or 0)
                compl_p = float(pricing.get("completion", 0) or 0)
                if ":free" in mid or (prompt_p == 0 and compl_p == 0):
                    free_models.append(mid)

            if free_models:
                priority = [
                    "nvidia/nemotron-3.5-lightning:free",
                    "liquid/lfm-2.5-2.6b:free",
                    "thinkingmachines/inkling:free",
                    "google/gemma-4-26b-a4b-it:free"
                ]
                sorted_models = []
                for p in priority:
                    if p in free_models:
                        sorted_models.append(p)
                        free_models.remove(p)
                sorted_models.extend(free_models)
                _CACHED_OPENROUTER_MODELS = sorted_models
                return _CACHED_OPENROUTER_MODELS
    except Exception:
        pass

    _CACHED_OPENROUTER_MODELS = DEFAULT_OPENROUTER_FREE_MODELS
    return _CACHED_OPENROUTER_MODELS

def call_google_gemini(model_name, messages, api_key, temperature=0.7, timeout=25):
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

def call_openrouter(key, model, messages, temperature=0.7, timeout=25):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://github.com/ParakramaWelipitiya/Unified-AI-Gateway",
        "X-Title": "Unified AI Gateway",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    return requests.post(url, headers=headers, json=payload, timeout=timeout)

def call_openai_compatible(url, key, model, messages, temperature=0.7, timeout=25):
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
    providers = []
    if get_keys("gemini"):
        providers.append("Gemini")
    if get_keys("openrouter"):
        providers.append("OpenRouter")
    if get_keys("groq"):
        providers.append("Groq")
    if get_keys("deepseek"):
        providers.append("DeepSeek")
    return providers

def get_available_selection_options():
    options = []
    if get_keys("gemini"):
        options.append("Gemini (Auto-switch models)")
        models = fetch_google_models()
        for m in models[:4]:
            options.append(f"Gemini: {m}")
    if get_keys("openrouter"):
        options.append("OpenRouter (Auto-switch free models)")
        models = fetch_openrouter_models()
        for m in models[:5]:
            options.append(f"OpenRouter: {m}")
    if get_keys("groq"):
        options.append("Groq (llama-3.3-70b-versatile)")
    if get_keys("deepseek"):
        options.append("DeepSeek (deepseek-chat)")
    return options

def chat_with_fallback(messages, preferred_selection=None):
    """
    Multi-Key, Multi-Model Router:
    Supports Google AI Studio (Gemini), OpenRouter, Groq, and DeepSeek.
    """
    gemini_keys = get_keys("gemini")
    openrouter_keys = get_keys("openrouter")
    groq_keys = get_keys("groq")
    deepseek_keys = get_keys("deepseek")

    gemini_models = fetch_google_models()
    openrouter_models = fetch_openrouter_models()

    # Determine target and preferred model
    is_auto_router = (preferred_selection is None or preferred_selection.lower().strip() == "auto-router")
    preferred_gemini_model = None
    preferred_openrouter_model = None
    target_provider = None

    if preferred_selection and not is_auto_router:
        pref = preferred_selection.lower().strip()
        if pref.startswith("gemini:"):
            target_provider = "gemini"
            preferred_gemini_model = preferred_selection.split(":", 1)[1].strip()
        elif pref.startswith("openrouter:"):
            target_provider = "openrouter"
            preferred_openrouter_model = preferred_selection.split(":", 1)[1].strip()
        elif "gemini" in pref:
            target_provider = "gemini"
            # Auto-switch through all Gemini models
            preferred_gemini_model = None
        elif "openrouter" in pref:
            target_provider = "openrouter"
            # Auto-switch through all OpenRouter free models
            preferred_openrouter_model = None
        elif "groq" in pref:
            target_provider = "groq"
        elif "deepseek" in pref:
            target_provider = "deepseek"

    # Sequence of providers in fallback chain
    provider_order = []
    if target_provider:
        provider_order.append(target_provider)
    if is_auto_router:
        for p in ["gemini", "openrouter", "groq", "deepseek"]:
            if p not in provider_order:
                provider_order.append(p)

    for provider in provider_order:
        # -------------------------------------------------------------
        # 1. GEMINI PROVIDER (Google AI Studio)
        # -------------------------------------------------------------
        if provider == "gemini":
            if not gemini_keys:
                if target_provider == "gemini":
                    return "Error: No Gemini API keys configured. Run /setup to add keys.", "None"
                continue

            models_to_try = [preferred_gemini_model] if preferred_gemini_model else gemini_models

            for g_model in models_to_try:
                model_failed = False

                for key_idx, g_key in enumerate(gemini_keys, 1):
                    key_tag = f"Key #{key_idx} ({mask_key(g_key)})"
                    try:
                        resp = call_google_gemini(g_model, messages, g_key, timeout=25)

                        if resp.status_code == 200:
                            data = resp.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                text_parts = [p.get("text", "") for p in parts if "text" in p and p.get("text")]
                                full_text = "".join(text_parts).strip()

                                if full_text:
                                    provider_label = f"Google AI Studio ({g_model}) [Key #{key_idx}]"
                                    return full_text, provider_label

                                finish_reason = candidates[0].get("finishReason", "UNKNOWN")
                                print(f"[-] Gemini '{g_model}' returned empty text (finishReason: {finish_reason}). Trying next...")
                                continue

                        if resp.status_code in [429, 403]:
                            reason = ERROR_MAP.get(resp.status_code, f"HTTP {resp.status_code}")
                            if key_idx < len(gemini_keys):
                                print(f"[-] Gemini {key_tag} {reason}. Switching to Key #{key_idx + 1}...")
                                continue
                            else:
                                print(f"[-] All {len(gemini_keys)} Gemini key(s) rate-limited on '{g_model}'. Auto-switching to next model...")
                                model_failed = True
                                break

                        if resp.status_code in [404, 500, 502, 503, 504]:
                            reason = ERROR_MAP.get(resp.status_code, f"HTTP {resp.status_code}")
                            print(f"[-] Gemini model '{g_model}' ({reason}). Auto-switching to next model...")
                            model_failed = True
                            break

                    except requests.exceptions.Timeout:
                        print(f"[-] Gemini model '{g_model}' timed out on {key_tag}.")
                        if key_idx < len(gemini_keys):
                            continue
                        model_failed = True
                        break
                    except requests.exceptions.RequestException as e:
                        print(f"[-] Network error on Gemini ({g_model}): {e}.")
                        if key_idx < len(gemini_keys):
                            continue
                        model_failed = True
                        break

                # If user pinned a single specific Gemini model and it failed:
                if preferred_gemini_model and model_failed:
                    return (
                        f"Error: Selected model '{preferred_gemini_model}' is currently unavailable or rate-limited. "
                        f"All {len(gemini_keys)} configured API key(s) were exhausted. "
                        f"Run /setup to add keys or select Gemini (Auto-switch models).",
                        "None"
                    )

            if target_provider == "gemini":
                return "Error: All Gemini models are currently busy, rate-limited, or unavailable. Switch to Auto-Router or OpenRouter.", "None"

        # -------------------------------------------------------------
        # 2. OPENROUTER PROVIDER
        # -------------------------------------------------------------
        elif provider == "openrouter":
            if not openrouter_keys:
                if target_provider == "openrouter":
                    return "Error: No OpenRouter API keys configured. Run /setup to add keys.", "None"
                continue

            models_to_try = [preferred_openrouter_model] if preferred_openrouter_model else openrouter_models

            for o_model in models_to_try:
                model_failed = False

                for key_idx, o_key in enumerate(openrouter_keys, 1):
                    key_tag = f"Key #{key_idx} ({mask_key(o_key)})"
                    try:
                        resp = call_openrouter(o_key, o_model, messages, timeout=25)
                        if resp.status_code == 200:
                            data = resp.json()
                            choices = data.get("choices", [])
                            if choices:
                                content = choices[0].get("message", {}).get("content", "").strip()
                                if content:
                                    provider_label = f"OpenRouter ({o_model}) [Key #{key_idx}]"
                                    return content, provider_label

                        if resp.status_code in [429, 403]:
                            if key_idx < len(openrouter_keys):
                                print(f"[-] OpenRouter {key_tag} rate-limited on '{o_model}'. Trying Key #{key_idx + 1}...")
                                continue
                            else:
                                print(f"[-] All OpenRouter keys rate-limited on '{o_model}'. Auto-switching to next model...")
                                model_failed = True
                                break

                        if resp.status_code in [404, 500, 502, 503, 504]:
                            reason = ERROR_MAP.get(resp.status_code, f"HTTP {resp.status_code}")
                            print(f"[-] OpenRouter model '{o_model}' ({reason}). Auto-switching to next free model...")
                            model_failed = True
                            break

                    except requests.exceptions.RequestException as e:
                        print(f"[-] Network error connecting to OpenRouter ({o_model}): {e}. Trying next...")
                        if key_idx < len(openrouter_keys):
                            continue
                        model_failed = True
                        break

                # If user pinned a single specific OpenRouter model and it failed:
                if preferred_openrouter_model and model_failed:
                    return (
                        f"Error: Selected OpenRouter model '{preferred_openrouter_model}' is currently unavailable or rate-limited. "
                        f"All {len(openrouter_keys)} API key(s) exhausted. Run /setup to add keys or select OpenRouter (Auto-switch free models).",
                        "None"
                    )

            if target_provider == "openrouter":
                return "Error: All OpenRouter free models are currently busy, rate-limited, or unavailable. Switch to Auto-Router or Gemini.", "None"

        # -------------------------------------------------------------
        # 3. GROQ PROVIDER
        # -------------------------------------------------------------
        elif provider == "groq":
            if not groq_keys:
                if target_provider == "groq":
                    return "Error: No Groq API keys configured. Run /setup to add keys.", "None"
                continue

            groq_url = "https://api.groq.com/openai/v1/chat/completions"
            groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

            for q_model in groq_models:
                for key_idx, q_key in enumerate(groq_keys, 1):
                    key_tag = f"Key #{key_idx} ({mask_key(q_key)})"
                    try:
                        resp = call_openai_compatible(groq_url, q_key, q_model, messages, timeout=25)
                        if resp.status_code == 200:
                            data = resp.json()
                            content = data["choices"][0]["message"]["content"]
                            if content and content.strip():
                                return content.strip(), f"Groq ({q_model}) [Key #{key_idx}]"

                        if resp.status_code in [429, 502, 503, 504]:
                            if key_idx < len(groq_keys):
                                print(f"[-] Groq {key_tag} rate-limited. Trying Key #{key_idx + 1}...")
                                continue
                            print(f"[-] Groq ({q_model}) busy or exhausted. Falling back...")
                            break

                        friendly = ERROR_MAP.get(resp.status_code, f"HTTP {resp.status_code}")
                        print(f"[!] Groq Error: {friendly}")
                        break
                    except requests.exceptions.RequestException:
                        continue

        # -------------------------------------------------------------
        # 4. DEEPSEEK PROVIDER
        # -------------------------------------------------------------
        elif provider == "deepseek":
            if not deepseek_keys:
                if target_provider == "deepseek":
                    return "Error: No DeepSeek API keys configured. Run /setup to add keys.", "None"
                continue

            ds_url = "https://api.deepseek.com/chat/completions"
            for key_idx, ds_key in enumerate(deepseek_keys, 1):
                key_tag = f"Key #{key_idx} ({mask_key(ds_key)})"
                try:
                    resp = call_openai_compatible(ds_url, ds_key, "deepseek-chat", messages, timeout=25)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        if content and content.strip():
                            return content.strip(), f"DeepSeek (deepseek-chat) [Key #{key_idx}]"

                    if resp.status_code in [429, 502, 503, 504]:
                        if key_idx < len(deepseek_keys):
                            print(f"[-] DeepSeek {key_tag} rate-limited. Trying Key #{key_idx + 1}...")
                            continue
                        break
                except requests.exceptions.RequestException:
                    continue

    return "Error: All configured AI providers, models, and API keys are rate-limited, invalid, or unavailable. Run /setup to add fresh keys.", "None"
