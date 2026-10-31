import sys
from router import (
    chat_with_fallback,
    get_available_selection_options,
    fetch_google_models
)

def show_help():
    print("\nCommands:")
    print("  /switch  - Change AI models or toggle Auto-Router")
    print("  /refresh - Fetch and update latest models from Google AI Studio")
    print("  /models  - View list of available Gemini models")
    print("  exit     - Close the terminal\n")

def main():
    print("=== Unified AI Gateway Terminal ===")
    print("Native Google AI Studio Integration & Multi-Model Auto-Failover Enabled.")
    show_help()

    conversation_history = [
        {"role": "system", "content": "You are a helpful AI assistant."}
    ]

    # None = Auto-Router is active (automatically tries Gemini with model auto-switching, then fallbacks)
    current_selection = None

    while True:
        try:
            prompt_label = current_selection if current_selection else "Auto-Router"
            user_input = input(f"\nYou [{prompt_label}]: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Unified AI Gateway. Goodbye!")
            break

        cleaned_input = user_input.strip()

        if not cleaned_input:
            continue

        if cleaned_input.lower() in ['exit', 'quit']:
            print("Exiting Unified AI Gateway. Goodbye!")
            break

        if cleaned_input.lower() == "/refresh":
            print("[*] Fetching updated model list from Google AI Studio...")
            models = fetch_google_models(force_refresh=True)
            print(f"[+] Successfully refreshed {len(models)} Gemini models from Google AI Studio.")
            continue

        if cleaned_input.lower() == "/models":
            models = fetch_google_models()
            print("\n--- Available Gemini Models (Google AI Studio) ---")
            for idx, m in enumerate(models, 1):
                print(f"  {idx}. {m}")
            print("--------------------------------------------------")
            continue

        if cleaned_input.lower() == "/switch":
            options = get_available_selection_options()
            print("\n--- Model / Provider Selection ---")
            print("[0] Auto-Router (Default: Auto-switch through models & providers)")
            for i, name in enumerate(options, 1):
                print(f"[{i}] {name}")

            try:
                choice = input("\nSelect a number: ").strip()
                choice_idx = int(choice)
                if choice_idx == 0:
                    current_selection = None
                    print("--> Switched to Auto-Router.")
                elif 1 <= choice_idx <= len(options):
                    current_selection = options[choice_idx - 1]
                    print(f"--> Switched to {current_selection}.")
                else:
                    print("--> Invalid selection. No changes made.")
            except ValueError:
                print("--> Invalid input. Please type a valid number.")

            continue

        conversation_history.append({"role": "user", "content": cleaned_input})

        print("\nThinking...")
        response_text, provider_used = chat_with_fallback(conversation_history, current_selection)

        print(f"\nAI (via {provider_used}):\n{response_text}")

        if provider_used != "None":
            conversation_history.append({"role": "assistant", "content": response_text})

if __name__ == "__main__":
    main()
