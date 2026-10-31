from router import chat_with_fallback, get_available_providers

def main():
    print("=== Unified AI Terminal Started ===")
    print("Commands:")
    print("  /switch  - Change AI models")
    print("  exit     - Close the terminal\n")
    
    conversation_history = [
        {"role": "system", "content": "You are a helpful AI assistant."}
    ]
    
    current_model = None  # None means Auto-Router is active

    while True:
        user_input = input("\nYou: ")
        
        if user_input.lower() in ['exit', 'quit']:
            break
            
        # Intercept the switch command
        if user_input.strip() == "/switch":
            options = get_available_providers()
            print("\n--- Model Selection ---")
            print("[0] Auto-Router (Default Priority)")
            for i, name in enumerate(options):
                print(f"[{i+1}] {name}")
                
            choice = input("\nSelect a number: ")
            
            try:
                choice_idx = int(choice)
                if choice_idx == 0:
                    current_model = None
                    print("--> Switched to Auto-Router.")
                elif 1 <= choice_idx <= len(options):
                    current_model = options[choice_idx-1]
                    print(f"--> Switched to {current_model}.")
                else:
                    print("--> Invalid selection. No changes made.")
            except ValueError:
                print("--> Invalid input. Please type a number.")
            
            # Skip sending the command to the AI
            continue
            
        conversation_history.append({"role": "user", "content": user_input})
        
        # Pass the preferred model into the router
        response_text, provider_used = chat_with_fallback(conversation_history, current_model)
        
        print(f"\nAI (via {provider_used}):\n{response_text}")
        
        if provider_used != "None":
            conversation_history.append({"role": "assistant", "content": response_text})

if __name__ == "__main__":
    main()