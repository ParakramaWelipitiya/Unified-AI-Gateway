# Unified AI Gateway

A high-performance Python gateway and terminal interface that pools free-tier API keys from multiple LLM providers (**Google AI Studio Gemini**, **OpenRouter**, **Groq**, **DeepSeek**) with an **Antigravity CLI-style UI**, **Multi-Key Pooling per Model**, and a **Strict Priority Context Engine** (`rules.md` ➜ `notes.md` ➜ `knowledge_base.md`).

---

## Supported Free-Tier Providers

| Provider | Best Free Models | Daily Quota / Rate Limits | Free Tier Features |
| :--- | :--- | :--- | :--- |
| **Google AI Studio** | `gemini-3.5-flash`, `gemini-3.1-flash-lite`, `gemini-pro-latest` | 15 RPM / 1,500 RPD | Native Google API, fastest response times, 1M context window |
| **OpenRouter** | `meta-llama/llama-3.3-70b-instruct:free`, `deepseek/deepseek-r1:free`, `qwen/qwen-2.5-coder-32b-instruct:free` | 20 RPM / 200 RPD | Massive catalog of free `:free` models across providers |
| **Groq** | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant` | 30 RPM / 14,400 RPD | World's fastest LPU inference (500+ tokens/sec) |
| **DeepSeek Platform** | `deepseek-chat` | Initial trial credits | Strong reasoning & coding capabilities |

---

## Key Features

### 1. Interactive Setup & Multi-Key Pooling (`/setup`)
- **Interactive In-Terminal Setup:** Configure your API keys directly inside the terminal without manually editing `.env`.
- **Multi-Key Pooling per Provider:** Add multiple free-tier keys for the same provider (e.g. 2–3 Google Gemini keys or OpenRouter keys).
- **Automatic Key Rotation on Rate Limits (429/403):** If Key #1 hits a usage cap or rate limit, the router silently rotates to Key #2 for the same model.
- **Failover Logic:**
  - In **Auto-Router** mode: cascades through all keys for Gemini ➜ OpenRouter ➜ Groq ➜ DeepSeek.
  - In **Selected Model** mode: tests all configured keys for that model; if all keys are exhausted, displays a clear message rather than silently switching models.

### 2. Live Context Update (`/update`)
- The `/update` command automatically re-indexes your codebase directly from the **current working directory** (`os.getcwd()`), refreshing `knowledge.json` and generating an up-to-date, human-readable `knowledge_base.md`.

### 3. Substantive Semantic Chunking
- Code-aware boundary detection splits code on `class`, `def`, and `async def` while ignoring comment dividers (`# ---`), ensuring every retrieved chunk contains real, functional code.

### 4. Strict Priority Context Flow
1. **Priority 1: `rules.md` (Golden Rules & Hard Constraints)**
   - Highest priority. Non-negotiable project policies.
   - Command: `/addrule <rule>` and `/rules`.
2. **Priority 2: `notes.md` (Developer Memory & Architectural Notes)**
   - Medium priority. Explicit developer facts, decisions, and documentation notes.
   - Command: `/addnote <title> | <content>` and `/notes`.
3. **Priority 3: `knowledge_base.md` (Codebase & Documents)**
   - Supporting context. Codebase files, functions, and documentation chunks.
   - Command: `/add <path>` or `/update`.

### 5. Antigravity CLI-Style Terminal UI
- Multi-line bracketed input prompt with live status badges:
  ```text
  ╭─[ ◆ Test ]─[ ⟡ gemini-3.5-flash ]─[ ⚡ RAG:ON ]
  ╰─❯ 
  ```
- Tab autocompletion for slash commands, files, and project names.
- Native Markdown formatting for headers, syntax-highlighted code blocks, bold, lists, and tables.
- Protected query cache (prevents caching empty or error responses).

---

## Installation & Setup

1. **Clone the repository:**
```bash
git clone https://github.com/ParakramaWelipitiya/Unified-AI-Gateway.git
cd Unified-AI-Gateway
```

2. **Activate your virtual environment:**
```powershell
.\venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install requests python-dotenv prompt_toolkit
```

4. **Launch the terminal & run `/setup`:**
```bash
python main.py
```
Type `/setup` inside the terminal to add and pool your API keys.

---

## Commands Guide

### API Keys & Configuration
- `/setup`          - Interactive wizard to add, pool, or view API keys (supports multiple keys per provider)
- `/update [path]`   - Re-index and sync context from path (or current working directory if omitted)

### Priority Context & Memory
- `/addrule <rule>` - Add a golden rule to `rules.md` (Priority 1)
- `/rules`          - View active project rules
- `/addnote <t>|<c>`- Add a developer memory note to `notes.md` (Priority 2)
- `/notes`          - View all saved notes
- `/add <path>`     - Index a single file or entire folder into `knowledge_base.md` (Priority 3)
- `/search <query>` - Hybrid test-search RAG retrieval without calling LLM (0 tokens)
- `/context`        - View storage path, chunk count, and index stats
- `/clear-rag [id]`   - Delete the project's RAG storage folder and all associated data

### Routing & Models
- `/project <name>` - Switch active project namespace
- `/switch`         - Switch model or select Auto-Router
- `/refresh`        - Fetch live model list from Google AI Studio
- `/models`         - Display all available Gemini models
- `/rag [on|off]`   - Toggle RAG retrieval
- `exit` or `quit`  - Exit terminal
