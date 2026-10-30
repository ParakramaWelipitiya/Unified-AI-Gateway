from router import chat_with_fallback

def main():
    print("=== Unified AI Terminal Started ===")
    print("Type 'exit' or 'quit' to close.\n")
    
    # Store chat history so the AI remembers context
    conversation_history = [
        {"role": "system", "content": "You are a helpful AI assistant."}
    ]

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit']:
            break
            
        # Add user message to history
        conversation_history.append({"role": "user", "content": user_input})
        
        # Get response from the router
        response_text, provider_used = chat_with_fallback(conversation_history)
        
        print(f"\nAI (via {provider_used}):\n{response_text}")
        
        # Add AI response to history
        if provider_used != "None":
            conversation_history.append({"role": "assistant", "content": response_text})

if __name__ == "__main__":
    main()