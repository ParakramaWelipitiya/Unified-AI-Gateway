# Unified AI Gateway

A lightweight, zero-dependency Python router that pools free-tier API keys from multiple LLM providers into a single, uninterrupted conversational interface. 

When a provider reaches its rate limit (429 error), the gateway silently catches the exception and instantly routes your prompt to the next available model in the fallback chain.

## Features
* **Automatic Failover:** Never hit a usage cap. If Groq limits you, it instantly switches to DeepSeek, then Gemini.
* **$0 Budget Architecture:** Designed exclusively around free-tier OpenAI-compatible endpoints.
* **Context Memory:** Maintains conversation history across different models during failover.
* **Lightweight:** Built natively with Python 3.13. Requires no heavy proxy servers or containerization—just `requests`.
* **Modular Design:** The `router.py` core logic is decoupled from the UI, making it drop-in ready for a FastAPI backend or a CustomTkinter desktop app.

## Prerequisites
* Python 3.10+ (Tested on Python 3.13)
* Free API keys from at least one supported provider:
  * [Groq Console](https://console.groq.com/)
  * [DeepSeek Platform](https://platform.deepseek.com/)
  * [Google AI Studio (Gemini)](https://aistudio.google.com/)

## Installation & Setup

1. **Clone the repository:**
```bash
git clone https://github.com/ParakramaWelipitiya/Unified-AI-Gateway.git
cd Custom-AI-Router
```

2. **Create and activate a virtual environment:**
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. **Install the required libraries:**
```bash
pip install requests python-dotenv
```

4. **Configure your API keys:**
```bash
Create a .env file in the root directory and add your free tier keys:

Code snippet
GROQ_API_KEY="your_groq_key_here"
DEEPSEEK_API_KEY="your_deepseek_key_here"
GEMINI_API_KEY="your_gemini_key_here"
```

5. **Start the interactive terminal session by running:**
```bash
python main.py
```
(To exit the session, type exit or quit.)

## How the Routing Logic Works
The system leverages the fact that most modern AI providers offer OpenAI-compatible API endpoints. Instead of writing custom parsing logic for every model, the chat_with_fallback() function generates a standard JSON payload.

It iterates through the PROVIDERS list in router.py. If a 429 Too Many Requests HTTP status is returned, the loop skips to the next dictionary object in the array, maintaining the exact same user context without dropping the request.

## Roadmap
[x] CLI Terminal Interface

[ ] Integration with a FastAPI microservice backend

[ ] Desktop GUI wrapper using CustomTkinter / PyQt6

