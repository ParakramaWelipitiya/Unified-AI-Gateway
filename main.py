import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from router import (
    chat_with_fallback,
    get_available_selection_options,
    fetch_google_models
)
from rag import rag_engine
from keys import (
    get_keys,
    add_keys,
    remove_key,
    clear_keys,
    mask_key,
    PROVIDERS_MAP
)
from ui import (
    C,
    print_banner,
    print_help,
    render_prompt_bar,
    render_priority_flow,
    render_ai_response,
    render_cache_hit,
    print_status
)

# Optional rich autocompletion using prompt_toolkit
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion, PathCompleter
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import ANSI
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

COMMAND_REGISTRY = {
    "/setup": "Interactive API Key setup & multi-key pooling",
    "/update": "Update context from path (or current directory if omitted)",
    "/switch": "Select AI model or Auto-Router",
    "/refresh": "Refresh Google AI Studio models",
    "/models": "List Google Gemini models",
    "/project": "Switch or create project context",
    "/add": "Index a file or folder into RAG",
    "/addnote": "Add developer memory note (notes.md)",
    "/addrule": "Add golden project rule (rules.md)",
    "/rules": "View active project rules",
    "/notes": "View developer notes",
    "/search": "Test RAG search locally (0 tokens)",
    "/rag": "Toggle RAG context retrieval",
    "/rag on": "Enable RAG context retrieval",
    "/rag off": "Disable RAG context retrieval",
    "/context": "View RAG stats & storage paths",
    "/clear-rag": "Delete RAG folder and all data for project",
    "/help": "Display command overview",
    "exit": "Exit the application",
    "quit": "Exit the application"
}

if PROMPT_TOOLKIT_AVAILABLE:
    class AntigravityCompleter(Completer):
        """
        Antigravity-style Tab Completer:
        - Completes slash commands when typing '/'
        - Completes file/directory paths after '/add '
        - Completes available project names after '/project '
        """
        def __init__(self, commands, rag_mgr):
            self.commands = commands
            self.rag = rag_mgr
            self.path_completer = PathCompleter(expanduser=True)

        def get_completions(self, document, complete_event):
            text = document.text_before_cursor

            # File/Folder path completion for /add or /update
            if text.startswith("/add ") or text.startswith("/update "):
                prefix_len = 5 if text.startswith("/add ") else 8
                sub_text = text[prefix_len:]
                sub_doc = document.__class__(sub_text, cursor_position=len(sub_text))
                for comp in self.path_completer.get_completions(sub_doc, complete_event):
                    yield comp
                return

            # Project name completion for /project
            if text.startswith("/project "):
                sub_text = text[9:]
                for p in self.rag.list_projects():
                    if p.lower().startswith(sub_text.lower()):
                        yield Completion(p, start_position=-len(sub_text), display=p, display_meta="Project")
                return

            # Command autocompletion
            word = document.get_word_before_cursor(WORD=True)
            search_key = text if text.startswith("/") else word

            if search_key:
                for cmd, meta in self.commands.items():
                    if cmd.lower().startswith(search_key.lower()):
                        start_pos = -len(search_key)
                        yield Completion(cmd, start_position=start_pos, display=cmd, display_meta=meta)

    auto_style = Style.from_dict({
        'completion-menu.completion': 'bg:#2b2b2b #00d7ff',
        'completion-menu.completion.current': 'bg:#005f87 #ffffff bold',
        'completion-menu.meta.completion': 'bg:#1e1e1e #888888 italic',
        'completion-menu.meta.completion.current': 'bg:#005f87 #ffff87',
    })

def run_setup_wizard():
    """Interactive API Key Setup & Multi-Key Pooling Wizard."""
    print(f"\n{C.BOLD}{C.BRIGHT_CYAN}╔══════════════════════════════════════════════════════════════════╗{C.RESET}")
    print(f"{C.BOLD}{C.BRIGHT_CYAN}║                  API KEY SETUP & POOLING WIZARD                  ║{C.RESET}")
    print(f"{C.BOLD}{C.BRIGHT_CYAN}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
    print(f"{C.DIM}Pool multiple free-tier keys per provider for automatic failover.{C.RESET}\n")

    while True:
        gem_keys = get_keys("gemini")
        or_keys = get_keys("openrouter")
        groq_keys = get_keys("groq")
        ds_keys = get_keys("deepseek")

        print(f"\n{C.BRIGHT_YELLOW}Configured Provider Keys:{C.RESET}")
        print(f"  {C.CYAN}[1]{C.RESET} Google AI Studio (Gemini) : {C.GREEN}{len(gem_keys)}{C.RESET} active key(s)")
        print(f"  {C.CYAN}[2]{C.RESET} OpenRouter                : {C.GREEN}{len(or_keys)}{C.RESET} active key(s)")
        print(f"  {C.CYAN}[3]{C.RESET} Groq                      : {C.GREEN}{len(groq_keys)}{C.RESET} active key(s)")
        print(f"  {C.CYAN}[4]{C.RESET} DeepSeek                  : {C.GREEN}{len(ds_keys)}{C.RESET} active key(s)")
        print(f"  {C.CYAN}[5]{C.RESET} View all keys (masked)")
        print(f"  {C.CYAN}[6]{C.RESET} Remove / Clear keys")
        print(f"  {C.CYAN}[0]{C.RESET} Return to Terminal\n")

        choice = input(f"{C.CYAN}Select option [0-6]: {C.RESET}").strip()

        if choice in ['0', 'exit', 'q', '']:
            print_status("Setup complete. Back in terminal.", "info")
            break
        elif choice == '1':
            _add_provider_keys("gemini", "Google AI Studio (Gemini)")
        elif choice == '2':
            _add_provider_keys("openrouter", "OpenRouter")
        elif choice == '3':
            _add_provider_keys("groq", "Groq")
        elif choice == '4':
            _add_provider_keys("deepseek", "DeepSeek")
        elif choice == '5':
            _view_masked_keys()
        elif choice == '6':
            _remove_keys_wizard()
        else:
            print_status("Invalid selection. Choose a number 0-6.", "warning")

def _add_provider_keys(provider, display_name):
    current = get_keys(provider)
    print(f"\n{C.BOLD}{C.BRIGHT_CYAN}--- Configure {display_name} Keys ---{C.RESET}")
    print(f"Currently active keys: {len(current)}")
    for idx, k in enumerate(current, 1):
        print(f"  Key #{idx}: {mask_key(k)}")

    print(f"\n{C.DIM}Tip: You can paste a single key or multiple keys separated by commas.{C.RESET}")
    new_input = input(f"Enter {display_name} key(s) (or press Enter to cancel): ").strip()
    if not new_input:
        return

    success, msg = add_keys(provider, new_input)
    if success:
        print_status(msg, "success")
    else:
        print_status(msg, "error")

def _view_masked_keys():
    print(f"\n{C.BOLD}{C.BRIGHT_CYAN}--- All Configured Keys ---{C.RESET}")
    for prov in ["gemini", "openrouter", "groq", "deepseek"]:
        keys = get_keys(prov)
        name = PROVIDERS_MAP[prov]["display"]
        if not keys:
            print(f"  {C.WHITE}{name:25s}:{C.RESET} {C.GRAY}None configured{C.RESET}")
        else:
            masked = ", ".join([f"#{i+1}: {mask_key(k)}" for i, k in enumerate(keys)])
            print(f"  {C.WHITE}{name:25s}:{C.RESET} {C.GREEN}{masked}{C.RESET}")
    print("--------------------------------------------------")

def _remove_keys_wizard():
    print(f"\n{C.BOLD}{C.BRIGHT_YELLOW}--- Remove / Clear Keys ---{C.RESET}")
    print("  [1] Google AI Studio (Gemini)")
    print("  [2] OpenRouter")
    print("  [3] Groq")
    print("  [4] DeepSeek")
    print("  [0] Cancel")
    prov_choice = input(f"{C.CYAN}Select provider to manage: {C.RESET}").strip()
    p_map = {"1": "gemini", "2": "openrouter", "3": "groq", "4": "deepseek"}
    prov = p_map.get(prov_choice)
    if not prov:
        return

    keys = get_keys(prov)
    if not keys:
        print_status(f"No keys configured for {PROVIDERS_MAP[prov]['display']}.", "info")
        return

    print(f"\nActive keys for {PROVIDERS_MAP[prov]['display']}:")
    for idx, k in enumerate(keys, 1):
        print(f"  [{idx}] Key #{idx}: {mask_key(k)}")
    print(f"  [C] Clear ALL keys for {PROVIDERS_MAP[prov]['display']}")
    print("  [0] Cancel")

    k_choice = input(f"{C.CYAN}Select key number to remove: {C.RESET}").strip()
    if k_choice.lower() == 'c':
        clear_keys(prov)
        print_status(f"Cleared all keys for {PROVIDERS_MAP[prov]['display']}.", "success")
    elif k_choice.isdigit() and 1 <= int(k_choice) <= len(keys):
        success, msg = remove_key(prov, int(k_choice))
        print_status(msg, "success" if success else "error")

def main():
    print_banner()
    print_help()

    conversation_history = [
        {"role": "system", "content": "You are a concise, accurate AI software engineering assistant. Format your answers clearly using Markdown."}
    ]

    current_selection = None

    session = None
    if PROMPT_TOOLKIT_AVAILABLE:
        session = PromptSession(
            completer=AntigravityCompleter(COMMAND_REGISTRY, rag_engine),
            history=InMemoryHistory(),
            style=auto_style
        )

    while True:
        try:
            model_display = current_selection if current_selection else "Auto-Router (gemini-3.5-flash)"
            bar_top, bar_bottom = render_prompt_bar(rag_engine.project, model_display, rag_engine.enabled)
            print(bar_top)

            if session:
                user_input = session.prompt(ANSI(bar_bottom))
            else:
                user_input = input(bar_bottom)

        except (KeyboardInterrupt, EOFError):
            print(f"\n{C.YELLOW}Exiting Unified AI Gateway. Goodbye!{C.RESET}")
            break

        cleaned_input = user_input.strip()

        if not cleaned_input:
            continue

        if cleaned_input.lower() in ['exit', 'quit']:
            print(f"{C.YELLOW}Exiting Unified AI Gateway. Goodbye!{C.RESET}")
            break

        if cleaned_input.lower() in ['/help', 'help']:
            print_help()
            continue

        # -------------------------------------------------------------
        # SETUP WIZARD (API Keys Configuration & Pooling)
        # -------------------------------------------------------------
        if cleaned_input.lower() == "/setup":
            run_setup_wizard()
            continue

        # -------------------------------------------------------------
        # CONTEXT UPDATE (/update [path] or defaults to os.getcwd())
        # -------------------------------------------------------------
        if cleaned_input.lower().startswith("/update"):
            parts = cleaned_input.split(maxsplit=1)
            target = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else None
            display_target = target if target else os.getcwd()
            print_status(f"Updating context from: {C.BOLD}{display_target}{C.RESET} ...", "action")
            success, msg = rag_engine.update_context(target)
            if success:
                print_status(msg, "success")
            else:
                print_status(msg, "error")
            continue

        # -------------------------------------------------------------
        # PRIORITY 1: RULES COMMANDS (rules.md)
        # -------------------------------------------------------------
        if cleaned_input.lower().startswith("/addrule "):
            rule_text = cleaned_input[9:].strip()
            if rule_text:
                msg = rag_engine.add_rule(rule_text)
                print_status(f"{msg} ({C.BOLD}rules.md{C.RESET})", "success")
            else:
                print_status("Usage: /addrule <strict project rule>", "warning")
            continue

        if cleaned_input.lower() == "/rules":
            rules = rag_engine.get_rules_list()
            print(f"\n{C.BOLD}{C.BRIGHT_MAGENTA}━━━ ACTIVE PROJECT RULES (rules.md - Priority 1) ━━━{C.RESET}")
            if not rules:
                print(f"  {C.GRAY}No active rules defined for '{rag_engine.project}'. Use /addrule <rule>{C.RESET}")
            else:
                for idx, r in enumerate(rules, 1):
                    print(f"  {C.BRIGHT_MAGENTA}{idx}.{C.RESET} {r}")
            print(f"{C.BOLD}{C.BRIGHT_MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.RESET}")
            continue

        # -------------------------------------------------------------
        # PRIORITY 2: NOTES COMMANDS (notes.md)
        # -------------------------------------------------------------
        if cleaned_input.lower().startswith("/addnote "):
            body = cleaned_input[9:].strip()
            if "|" in body:
                title, content = body.split("|", 1)
                title = title.strip()
                content = content.strip()
            else:
                title = "Quick Note"
                content = body

            count = rag_engine.add_note(title, content)
            print_status(f"Added note '{title}' ({count} chunks) to {C.BOLD}notes.md{C.RESET} (Priority 2)", "success")
            continue

        if cleaned_input.lower() == "/notes":
            notes = rag_engine.get_notes_content()
            print(f"\n{C.BOLD}{C.BRIGHT_BLUE}━━━ DEVELOPER NOTES (notes.md - Priority 2) ━━━{C.RESET}")
            print(notes)
            print(f"{C.BOLD}{C.BRIGHT_BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.RESET}")
            continue

        # -------------------------------------------------------------
        # PRIORITY 3: KNOWLEDGE BASE COMMANDS (knowledge_base.md)
        # -------------------------------------------------------------
        if cleaned_input.lower().startswith("/add "):
            target_path = cleaned_input[5:].strip().strip('"').strip("'")
            if os.path.isdir(target_path):
                print_status(f"Recursively indexing directory '{target_path}' into knowledge base...", "action")
                success, msg = rag_engine.add_directory(target_path)
            else:
                success, msg = rag_engine.add_file(target_path)

            if success:
                print_status(msg, "success")
                kb_path = os.path.join(rag_engine.get_project_dir(), 'knowledge_base.md')
                print(f"  {C.DIM}Inspect in Markdown: {kb_path}{C.RESET}")
            else:
                print_status(msg, "error")
            continue

        # -------------------------------------------------------------
        # Zero-Token RAG Search Inspector
        # -------------------------------------------------------------
        if cleaned_input.lower().startswith("/search"):
            parts = cleaned_input.split(maxsplit=1)
            query = parts[1].strip() if len(parts) > 1 else ""
            if not query:
                print_status("Usage: /search <query to test RAG retrieval>", "warning")
                continue

            print_status(f"Testing hybrid search for '{query}' (0 tokens consumed)...", "action")
            results = rag_engine.search_context(query, top_k=4)
            if not results:
                print_status("No matching context chunks found above similarity threshold.", "warning")
            else:
                print(f"\n{C.BOLD}{C.BRIGHT_CYAN}━━━ RETRIEVED CHUNKS ({len(results)} matches) ━━━{C.RESET}")
                for rank, (score, ch) in enumerate(results, 1):
                    src = ch.get("breadcrumb") or ch.get("source")
                    is_note = f" {C.BRIGHT_BLUE}[NOTE]{C.RESET}" if ch.get("is_note") else ""
                    preview = ch.get("text", "").replace("\n", " ")[:130]
                    print(f"  {C.CYAN}[{rank}]{C.RESET} Score: {C.GREEN}{score:.3f}{C.RESET}{is_note} │ Source: {C.WHITE}{src}{C.RESET}")
                    print(f"      {C.GRAY}\"{preview}...\"{C.RESET}")
                print(f"{C.BOLD}{C.BRIGHT_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.RESET}")
            continue

        # -------------------------------------------------------------
        # Project Switching
        # -------------------------------------------------------------
        if cleaned_input.lower().startswith("/project"):
            parts = cleaned_input.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip():
                new_project = rag_engine.set_project(parts[1].strip())
                print_status(f"Switched project context to: '{C.BOLD}{new_project}{C.RESET}'", "success")
            else:
                current_p = rag_engine.project
                all_p = rag_engine.list_projects()
                print(f"\n{C.CYAN}Active Project:{C.RESET} {C.BOLD}{current_p}{C.RESET}")
                print(f"{C.CYAN}Available Projects:{C.RESET} {', '.join(all_p)}")
                print(f"{C.DIM}Usage: /project <name> to switch or create.{C.RESET}")
            continue

        # -------------------------------------------------------------
        # Toggle RAG
        # -------------------------------------------------------------
        if cleaned_input.lower().startswith("/rag"):
            parts = cleaned_input.split(maxsplit=1)
            if len(parts) > 1:
                arg = parts[1].strip().lower()
                if arg == "on":
                    rag_engine.enabled = True
                    print_status("RAG context retrieval ENABLED.", "success")
                elif arg == "off":
                    rag_engine.enabled = False
                    print_status("RAG context retrieval DISABLED.", "warning")
                else:
                    print_status("Usage: /rag on  or  /rag off", "warning")
            else:
                state = f"{C.GREEN}ENABLED{C.RESET}" if rag_engine.enabled else f"{C.RED}DISABLED{C.RESET}"
                print(f"RAG is currently {state}.")
            continue

        # -------------------------------------------------------------
        # Context Breakdown & Stats
        # -------------------------------------------------------------
        if cleaned_input.lower() in ["/context", "/raginfo"]:
            stats = rag_engine.get_stats()
            print(f"\n{C.BOLD}{C.BRIGHT_CYAN}━━━ PROJECT CONTEXT STATUS: {stats['project']} ━━━{C.RESET}")
            print(f"  {C.CYAN}RAG Status:{C.RESET} {'ACTIVE' if stats['enabled'] else 'DISABLED'}")
            print(f"  {C.BRIGHT_MAGENTA}Priority 1 (Rules):{C.RESET} {stats['rules_count']} active rule(s) in {C.BOLD}rules.md{C.RESET}")
            print(f"  {C.BRIGHT_BLUE}Priority 2 (Notes):{C.RESET} {stats['notes_count']} note chunk(s) in {C.BOLD}notes.md{C.RESET}")
            print(f"  {C.BRIGHT_GREEN}Priority 3 (Knowledge):{C.RESET} {stats['total_chunks']} total chunk(s) in {C.BOLD}knowledge_base.md{C.RESET}")
            print(f"  {C.WHITE}Dense Google Embeddings:{C.RESET} {stats['dense_embeddings_count']}")
            print(f"  {C.WHITE}Cached Answers:{C.RESET} {stats['cached_queries']} query hashes in cache.json")
            print(f"  {C.GRAY}Storage Dir:{C.RESET} {stats['storage_path']}")
            print(f"{C.BOLD}{C.BRIGHT_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.RESET}")
            continue

        # -------------------------------------------------------------
        # Clear Project Context & Remove RAG Folder
        # -------------------------------------------------------------
        if cleaned_input.lower().startswith("/clear-rag"):
            parts = cleaned_input.split(maxsplit=1)
            target = parts[1].strip() if len(parts) > 1 else rag_engine.project
            confirm = input(f"{C.YELLOW}Completely delete RAG folder and all data for '{target}'? (y/n): {C.RESET}")
            if confirm.lower() in ['y', 'yes']:
                msg = rag_engine.clear_project(target)
                print_status(msg, "success")
            continue

        # -------------------------------------------------------------
        # Router Management Commands
        # -------------------------------------------------------------
        if cleaned_input.lower() == "/refresh":
            print_status("Updating live models list from Google AI Studio...", "action")
            models = fetch_google_models(force_refresh=True)
            print_status(f"Successfully refreshed {len(models)} Gemini models from Google AI Studio.", "success")
            continue

        if cleaned_input.lower() == "/models":
            models = fetch_google_models()
            print(f"\n{C.BOLD}{C.BRIGHT_CYAN}━━━ AVAILABLE GEMINI MODELS (Google AI Studio) ━━━{C.RESET}")
            for idx, m in enumerate(models, 1):
                star = f" {C.BRIGHT_YELLOW}(Fastest / Recommended){C.RESET}" if idx == 1 else ""
                print(f"  {C.CYAN}{idx:2d}.{C.RESET} {m}{star}")
            print(f"{C.BOLD}{C.BRIGHT_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.RESET}")
            continue

        if cleaned_input.lower() == "/switch":
            options = get_available_selection_options()
            print(f"\n{C.BOLD}{C.BRIGHT_CYAN}━━━ MODEL & ROUTER SELECTION ━━━{C.RESET}")
            print(f"  {C.CYAN}[0]{C.RESET} Auto-Router (Default: gemini-3.5-flash with auto-failover)")
            for i, name in enumerate(options, 1):
                print(f"  {C.CYAN}[{i}]{C.RESET} {name}")

            try:
                choice = input(f"\n{C.CYAN}Select option number: {C.RESET}").strip()
                choice_idx = int(choice)
                if choice_idx == 0:
                    current_selection = None
                    print_status("Switched to Auto-Router.", "success")
                elif 1 <= choice_idx <= len(options):
                    current_selection = options[choice_idx - 1]
                    print_status(f"Switched to {current_selection}.", "success")
                else:
                    print_status("Invalid selection. No changes made.", "warning")
            except ValueError:
                print_status("Invalid input. Please enter a number.", "warning")
            continue

        # -----------------------------------------------------------------
        # PROMPT PROCESSING: PRIORITY FLOW & CACHING
        # -----------------------------------------------------------------
        # 1. Zero-Cost Query Cache
        cached = rag_engine.get_cached_response(cleaned_input)
        if cached:
            render_cache_hit(cached['provider'], cached['response'])
            conversation_history.append({"role": "user", "content": cleaned_input})
            conversation_history.append({"role": "assistant", "content": cached['response']})
            continue

        # 2. Strict Priority Augmented Context (rules.md -> notes.md -> knowledge.md)
        augmented_prompt, stats = rag_engine.build_priority_augmented_prompt(cleaned_input)
        render_priority_flow(stats)

        # 3. Dynamic History Trimming
        if len(conversation_history) > 12:
            conversation_history = [conversation_history[0]] + conversation_history[-8:]

        temp_history = list(conversation_history)
        temp_history.append({"role": "user", "content": augmented_prompt})

        target_label = current_selection if current_selection else "Auto-Router"
        print(f"\n  {C.CYAN}◆ Thinking [{target_label}]...{C.RESET}")
        response_text, provider_used = chat_with_fallback(temp_history, current_selection)

        # Display result
        render_ai_response(provider_used, response_text)

        # Only cache and keep history if a valid non-empty response was generated
        if provider_used != "None" and response_text and not response_text.startswith("Error:"):
            conversation_history.append({"role": "user", "content": cleaned_input})
            conversation_history.append({"role": "assistant", "content": response_text})
            rag_engine.cache_response(cleaned_input, response_text, provider_used)

if __name__ == "__main__":
    main()
