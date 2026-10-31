# Unified AI Gateway

A lightweight, zero-dependency Python router that pools free-tier API keys from multiple LLM providers (Google AI Studio Gemini, Groq, DeepSeek) into a single, uninterrupted conversational interface.

When a model or provider reaches its rate limit (429), times out, or encounters a server error, the gateway silently catches the exception and instantly routes your prompt to the next available model in the fallback chain.

## Features
* **Native Google AI Studio Integration:** Calls Google's Gemini API directly using the native `generateContent` format instead of legacy OpenAI wrappers.
* **Intra-Gemini Model Auto-Switching:** If a Gemini model hits a rate limit (429) or is busy/deprecated, the router automatically fails over to the next Gemini model (e.g. `gemini-2.5-flash` -> `gemini-2.5-pro` -> `gemini-2.0-flash`, etc.).
* **Dynamic Model Updates from Google:** Fetches the latest available Gemini models dynamically directly from Google AI Studio (`GET /v1beta/models`).
* **Cross-Provider Automatic Failover:** If all Gemini models are exhausted or rate-limited, smoothly cascades to Groq and DeepSeek.
* **Context Memory:** Maintains complete conversation history and system instructions across models and providers during failover.
* **Lightweight & Decoupled:** Built with Python 3.10+ using just `requests` and `python-dotenv`. Core logic in `router.py` is fully decoupled from the UI for easy integration into FastAPI or GUI desktop apps.

## Prerequisites
* Python 3.10+ (Tested on Python 3.13 / 3.14)
* Free API keys from at least one supported provider:
  * [Google AI Studio (Gemini)](https://aistudio.google.com/)
  * [Groq Console](https://console.groq.com/)
  * [DeepSeek Platform](https://platform.deepseek.com/)

## Installation & Setup

1. **Clone the repository:**
```bash
git clone https://github.com/ParakramaWelipitiya/Unified-AI-Gateway.git
cd Unified-AI-Gateway
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
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY="your_gemini_api_key_here"
GROQ_API_KEY="your_groq_api_key_here"
DEEPSEEK_API_KEY="your_deepseek_api_key_here"
```

5. **Start the interactive terminal session:**
```bash
python main.py
```

### Commands in Terminal
- `/switch`  - Select a specific Gemini model, another provider, or return to Auto-Router
- `/refresh` - Fetch and update the latest model list dynamically from Google AI Studio
- `/models`  - View all currently active Gemini models from Google AI Studio
- `exit` / `quit` - Exit the terminal
