import os
import re
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

PROVIDERS_MAP = {
    "gemini": {
        "display": "Google AI Studio (Gemini)",
        "keys_var": "GEMINI_API_KEYS",
        "legacy_var": "GEMINI_API_KEY"
    },
    "openrouter": {
        "display": "OpenRouter",
        "keys_var": "OPENROUTER_API_KEYS",
        "legacy_var": "OPENROUTER_API_KEY"
    },
    "groq": {
        "display": "Groq",
        "keys_var": "GROQ_API_KEYS",
        "legacy_var": "GROQ_API_KEY"
    },
    "deepseek": {
        "display": "DeepSeek",
        "keys_var": "DEEPSEEK_API_KEYS",
        "legacy_var": "DEEPSEEK_API_KEY"
    }
}

def reload_env():
    load_dotenv(ENV_PATH, override=True)

def mask_key(key):
    if not key:
        return ""
    clean = key.strip()
    if len(clean) <= 10:
        return clean[:2] + "..." + clean[-2:]
    return clean[:6] + "..." + clean[-4:]

def get_keys(provider_name):
    """
    Returns list of active API keys for a provider from environment / .env.
    Supports multiple keys separated by comma or list.
    """
    reload_env()
    cfg = PROVIDERS_MAP.get(provider_name.lower())
    if not cfg:
        return []

    raw_keys = os.getenv(cfg["keys_var"], "")
    legacy_key = os.getenv(cfg["legacy_var"], "")

    keys_pool = []
    # Parse keys_var (comma separated)
    if raw_keys:
        for k in raw_keys.split(","):
            cleaned = k.strip().strip('"').strip("'")
            if cleaned and cleaned not in keys_pool:
                keys_pool.append(cleaned)

    # Include legacy key if not already present
    if legacy_key:
        cleaned_leg = legacy_key.strip().strip('"').strip("'")
        if cleaned_leg and cleaned_leg not in keys_pool:
            keys_pool.append(cleaned_leg)

    return keys_pool

def _read_env_lines():
    if not os.path.exists(ENV_PATH):
        return []
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        return f.readlines()

def _write_env_lines(lines):
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
    reload_env()

def add_keys(provider_name, new_keys_input):
    """
    Appends one or more comma-separated keys to the provider's pool in .env.
    """
    cfg = PROVIDERS_MAP.get(provider_name.lower())
    if not cfg:
        return False, f"Unknown provider: {provider_name}"

    current = get_keys(provider_name)
    added_count = 0

    # Parse user input (comma-separated or single)
    tokens = [t.strip().strip('"').strip("'") for t in new_keys_input.split(",") if t.strip()]
    for t in tokens:
        if t and t not in current:
            current.append(t)
            added_count += 1

    if added_count == 0:
        return True, f"Key(s) already exist for {cfg['display']}. Current count: {len(current)}"

    # Save to .env
    lines = _read_env_lines()
    joined_keys = ",".join(current)
    keys_var = cfg["keys_var"]
    legacy_var = cfg["legacy_var"]

    found_var = False
    found_leg = False
    new_lines = []

    for line in lines:
        if line.startswith(f"{keys_var}="):
            new_lines.append(f'{keys_var}="{joined_keys}"\n')
            found_var = True
        elif line.startswith(f"{legacy_var}="):
            # Keep primary key in legacy var for backwards compatibility
            new_lines.append(f'{legacy_var}="{current[0]}"\n')
            found_leg = True
        else:
            new_lines.append(line)

    if not found_var:
        new_lines.append(f'{keys_var}="{joined_keys}"\n')
    if not found_leg:
        new_lines.append(f'{legacy_var}="{current[0]}"\n')

    _write_env_lines(new_lines)
    return True, f"Added {added_count} new key(s) to {cfg['display']}. Total active keys: {len(current)}"

def remove_key(provider_name, key_index):
    """Removes a key by index (1-based)."""
    cfg = PROVIDERS_MAP.get(provider_name.lower())
    if not cfg:
        return False, f"Unknown provider: {provider_name}"

    current = get_keys(provider_name)
    if key_index < 1 or key_index > len(current):
        return False, "Invalid key index."

    removed = current.pop(key_index - 1)
    lines = _read_env_lines()
    joined_keys = ",".join(current)
    keys_var = cfg["keys_var"]
    legacy_var = cfg["legacy_var"]

    new_lines = []
    found_var = False
    found_leg = False

    for line in lines:
        if line.startswith(f"{keys_var}="):
            new_lines.append(f'{keys_var}="{joined_keys}"\n')
            found_var = True
        elif line.startswith(f"{legacy_var}="):
            primary = current[0] if current else ""
            new_lines.append(f'{legacy_var}="{primary}"\n')
            found_leg = True
        else:
            new_lines.append(line)

    if not found_var:
        new_lines.append(f'{keys_var}="{joined_keys}"\n')
    if not found_leg:
        primary = current[0] if current else ""
        new_lines.append(f'{legacy_var}="{primary}"\n')

    _write_env_lines(new_lines)
    return True, f"Removed key ({mask_key(removed)}) from {cfg['display']}."

def clear_keys(provider_name):
    """Clears all keys for a provider."""
    cfg = PROVIDERS_MAP.get(provider_name.lower())
    if not cfg:
        return False, f"Unknown provider: {provider_name}"

    lines = _read_env_lines()
    keys_var = cfg["keys_var"]
    legacy_var = cfg["legacy_var"]

    new_lines = []
    for line in lines:
        if line.startswith(f"{keys_var}=") or line.startswith(f"{legacy_var}="):
            continue
        new_lines.append(line)

    _write_env_lines(new_lines)
    return True, f"Cleared all keys for {cfg['display']}."
