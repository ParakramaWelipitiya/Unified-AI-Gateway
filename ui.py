import os
import sys
import re

# Enable UTF-8 encoding and VT100 ANSI sequences on Windows 10/11
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    getattr(sys.stderr, "reconfigure")(encoding="utf-8")
if sys.platform == "win32":
    os.system("")

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    GRAY = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    BG_DARK = "\033[48;5;236m"
    BG_CODE = "\033[48;5;235m"
    CODE_FG = "\033[38;5;222m"

def print_banner():
    banner = f"""
{C.BRIGHT_CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
║  {C.BOLD}{C.BRIGHT_WHITE}UNIFIED AI GATEWAY {C.RESET}{C.GRAY}│ Antigravity-Style Hybrid RAG & Google AI Studio{C.RESET}{C.BRIGHT_CYAN}         ║
║  {C.DIM}{C.CYAN}Priority Context: rules.md ➜ notes.md ➜ knowledge.md │ Tab Autocomplete{C.RESET}{C.BRIGHT_CYAN} ║
╚══════════════════════════════════════════════════════════════════════════════╝{C.RESET}"""
    print(banner)

def print_help():
    help_text = f"""
{C.BOLD}{C.BRIGHT_CYAN}━━━ COMMANDS OVERVIEW ({C.YELLOW}Press Tab to Autocomplete Commands{C.BRIGHT_CYAN}) ━━━━━━━━━━━━━━{C.RESET}
{C.BRIGHT_YELLOW}PRIORITY CONTEXT PIPELINE:{C.RESET}
  {C.BRIGHT_MAGENTA}/addrule <text>{C.RESET}   Add golden project rule ({C.BOLD}rules.md{C.RESET} - Highest Priority)
  {C.BRIGHT_MAGENTA}/rules{C.RESET}            View active project rules ({C.BOLD}rules.md{C.RESET})
  {C.BRIGHT_BLUE}/addnote <t>|<c>{C.RESET}  Add developer memory note ({C.BOLD}notes.md{C.RESET} - Medium Priority)
  {C.BRIGHT_BLUE}/notes{C.RESET}            View developer notes ({C.BOLD}notes.md{C.RESET})
  {C.BRIGHT_GREEN}/update [path]{C.RESET}    Update context from path (or current dir if omitted)
  {C.BRIGHT_GREEN}/add <path>{C.RESET}       Index a file OR folder recursively ({C.BOLD}knowledge_base.md{C.RESET})
  {C.BRIGHT_CYAN}/search <query>{C.RESET}   Test hybrid RAG search without calling LLM (0 tokens)
  {C.GRAY}/context{C.RESET}          Detailed project stats and chunk storage breakdown
  {C.GRAY}/clear-rag [id]{C.RESET}   Delete RAG folder and all data for project

{C.BRIGHT_YELLOW}ROUTING & GOOGLE AI STUDIO:{C.RESET}
  {C.WHITE}/setup{C.RESET}            Interactive API Key setup & multi-key pooling
  {C.WHITE}/project [name]{C.RESET}   Switch or create active project context
  {C.WHITE}/switch{C.RESET}           Change models or toggle Auto-Router
  {C.WHITE}/refresh{C.RESET}          Update available models live from Google AI Studio
  {C.WHITE}/models{C.RESET}           List all Google Gemini models
  {C.WHITE}/rag [on|off]{C.RESET}     Toggle context retrieval
  {C.WHITE}exit / quit{C.RESET}       Exit terminal
{C.BOLD}{C.BRIGHT_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.RESET}
"""
    print(help_text)

def render_prompt_bar(project, model_label, rag_enabled):
    """
    Renders an Antigravity CLI input bar with multi-line bracketed styling.
    """
    p_badge = f"{C.BOLD}{C.BRIGHT_MAGENTA}◆ {project}{C.RESET}"
    m_badge = f"{C.BRIGHT_CYAN}⟡ {model_label}{C.RESET}"
    rag_badge = f"{C.BRIGHT_GREEN}⚡ RAG:ON{C.RESET}" if rag_enabled else f"{C.GRAY}⚡ RAG:OFF{C.RESET}"

    bar_top = f"\n{C.GRAY}╭─{C.RESET}[ {p_badge} {C.RESET}]─[ {m_badge} {C.RESET}]─[ {rag_badge} {C.RESET}]"
    bar_bottom = f"{C.GRAY}╰─{C.BRIGHT_CYAN}❯{C.RESET} "
    return bar_top, bar_bottom

def render_priority_flow(stats):
    """Displays the exact context hierarchy injected into the prompt."""
    rules_c = stats.get("rules", 0)
    notes_c = stats.get("notes", 0)
    kb_c = stats.get("knowledge", 0)
    total = rules_c + notes_c + kb_c

    if total == 0:
        return

    r_str = f"{C.BRIGHT_MAGENTA}rules.md ({rules_c}){C.RESET}" if rules_c else f"{C.GRAY}rules.md (0){C.RESET}"
    n_str = f"{C.BRIGHT_BLUE}notes.md ({notes_c}){C.RESET}" if notes_c else f"{C.GRAY}notes.md (0){C.RESET}"
    k_str = f"{C.BRIGHT_GREEN}knowledge_base.md ({kb_c}){C.RESET}" if kb_c else f"{C.GRAY}knowledge_base.md (0){C.RESET}"

    badge = f"{C.DIM}⚡ Injected Priority Flow: {C.RESET}{r_str} {C.GRAY}➜{C.RESET} {n_str} {C.GRAY}➜{C.RESET} {k_str}"
    print(f"  {badge}")

# -------------------------------------------------------------
# Markdown Terminal Rendering Engine
# -------------------------------------------------------------
def format_inline_markdown(text):
    """
    Renders inline markdown elements cleanly using a placeholder-masking 
    strategy to prevent formatting rule bleed into code blocks.
    """
    # 1. Protect inline code spans by masking them
    code_spans = []
    
    def mask_code(match):
        code_spans.append(match.group(1))
        return f"\x00CODE_{len(code_spans) - 1}\x00"

    text = re.sub(r'`([^`]+)`', mask_code, text)

    # 2. Process remaining inline styling rules safely
    # Bold + Italic: ***text*** or ___text___
    text = re.sub(
        r'(\*{3}|_{3})(.+?)\1',
        lambda m: f"{C.BOLD}{C.ITALIC}{C.BRIGHT_WHITE}{m.group(2)}{C.RESET}",
        text
    )

    # Bold: **text** or __text__
    text = re.sub(
        r'(\*{2}|_{2})(.+?)\1',
        lambda m: f"{C.BOLD}{C.BRIGHT_WHITE}{m.group(2)}{C.RESET}",
        text
    )

    # Italic: *text* or _text_
    text = re.sub(
        r'(\*|_)(.+?)\1',
        lambda m: f"{C.ITALIC}{C.WHITE}{m.group(2)}{C.RESET}",
        text
    )

    # Markdown links: [text](url)
    text = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        lambda m: f"{C.UNDERLINE}{C.BRIGHT_BLUE}{m.group(1)}{C.RESET} {C.GRAY}({m.group(2)}){C.RESET}",
        text
    )

    # 3. Restore protected inline code blocks with custom styling
    def unmask_code(match):
        idx = int(match.group(1))
        content = code_spans[idx]
        return f"{C.CODE_FG}{C.BG_CODE} {content} {C.RESET}"

    text = re.sub(r'\x00CODE_(\d+)\x00', unmask_code, text)

    return text

def render_markdown(text):
    """
    Transforms raw Markdown into richly styled ANSI terminal output:
    - Fenced code blocks with language headers and borders
    - Headings (H1, H2, H3, H4) with distinctive icons & colors
    - Lists (bullet, numbered, checkbox)
    - Blockquotes
    - Horizontal rules
    - Inline formatting (bold, italic, code, links)
    """
    lines = text.splitlines()
    output_lines = []
    in_code_block = False
    code_lang = ""

    for line in lines:
        stripped = line.strip()

        # Handle fenced code block boundary
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = stripped[3:].strip() or "code"
                tag = f" {C.BOLD}{C.BRIGHT_YELLOW}[{code_lang}]{C.RESET} "
                border_len = max(10, 60 - len(code_lang))
                output_lines.append(f"{C.GRAY}  ┌──{tag}{'─' * border_len}┐{C.RESET}")
            else:
                in_code_block = False
                output_lines.append(f"{C.GRAY}  └{'─' * 66}┘{C.RESET}")
            continue

        # Inside code block
        if in_code_block:
            output_lines.append(f"{C.GRAY}  │{C.RESET}  {C.CODE_FG}{line}{C.RESET}")
            continue

        # Horizontal rule (--- or *** or ___)
        if re.match(r'^(\-{3,}|\*{3,}|\_{3,})$', stripped):
            output_lines.append(f"{C.GRAY}  {'─' * 66}{C.RESET}")
            continue

        # Headings
        if stripped.startswith("# "):
            title = format_inline_markdown(stripped[2:])
            output_lines.append(f"\n  {C.BOLD}{C.BRIGHT_MAGENTA}■ {title}{C.RESET}")
            continue
        if stripped.startswith("## "):
            title = format_inline_markdown(stripped[3:])
            output_lines.append(f"\n  {C.BOLD}{C.BRIGHT_CYAN}◆ {title}{C.RESET}")
            continue
        if stripped.startswith("### "):
            title = format_inline_markdown(stripped[4:])
            output_lines.append(f"\n  {C.BOLD}{C.BRIGHT_YELLOW}▲ {title}{C.RESET}")
            continue
        if stripped.startswith("#### "):
            title = format_inline_markdown(stripped[5:])
            output_lines.append(f"  {C.BOLD}{C.BRIGHT_BLUE}● {title}{C.RESET}")
            continue

        # Blockquote (> text)
        if stripped.startswith(">"):
            quote_text = format_inline_markdown(stripped.lstrip("> ").strip())
            output_lines.append(f"  {C.GRAY}▌{C.RESET} {C.ITALIC}{C.WHITE}{quote_text}{C.RESET}")
            continue

        # Checkbox list (- [x] or - [ ])
        if re.match(r'^[-*+]\s+\[([ xX])\]\s+', stripped):
            checked = "[x]" in stripped.lower()
            box = f"{C.BRIGHT_GREEN}[✓]{C.RESET}" if checked else f"{C.GRAY}[ ]{C.RESET}"
            item_text = format_inline_markdown(re.sub(r'^[-*+]\s+\[([ xX])\]\s+', '', stripped))
            output_lines.append(f"    {box} {item_text}")
            continue

        # Unordered bullet list (- or * or +)
        bullet_match = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        if bullet_match:
            indent = bullet_match.group(1)
            item_text = format_inline_markdown(bullet_match.group(2))
            output_lines.append(f"  {indent}{C.BRIGHT_CYAN}•{C.RESET} {item_text}")
            continue

        # Numbered list (1. 2. etc)
        numbered_match = re.match(r'^(\s*)(\d+)\.\s+(.*)', line)
        if numbered_match:
            indent = numbered_match.group(1)
            num = numbered_match.group(2)
            item_text = format_inline_markdown(numbered_match.group(3))
            output_lines.append(f"  {indent}{C.BRIGHT_YELLOW}{num}.{C.RESET} {item_text}")
            continue

        # Regular paragraph line
        output_lines.append(f"  {format_inline_markdown(line)}")

    return "\n".join(output_lines)

def render_ai_response(provider, text):
    """Formats AI response inside an Antigravity-styled bordered card with Markdown text features."""
    title = f"{C.BOLD}{C.BRIGHT_WHITE}AI {C.RESET}{C.CYAN}via {provider}{C.RESET}"
    header = f"{C.BRIGHT_CYAN}╭── {title} {C.BRIGHT_CYAN}{'─' * max(20, 60 - len(provider))}╮{C.RESET}"
    footer = f"{C.BRIGHT_CYAN}╰{'─' * max(30, 68)}╯{C.RESET}"

    formatted_body = render_markdown(text)

    print(f"\n{header}")
    print(formatted_body)
    print(f"{footer}\n")

def render_cache_hit(provider, text):
    """Formats a zero-cost cached response."""
    badge = f"{C.BRIGHT_GREEN}⚡ [ZERO-COST CACHE HIT] {C.RESET}{C.GRAY}(0 API calls, 0 tokens consumed){C.RESET}"
    print(f"\n  {badge}")
    render_ai_response(provider, text)

def print_status(msg, kind="info"):
    symbols = {
        "success": f"{C.BRIGHT_GREEN}[✓]{C.RESET}",
        "info": f"{C.BRIGHT_CYAN}[ℹ]{C.RESET}",
        "warning": f"{C.BRIGHT_YELLOW}[!]{C.RESET}",
        "error": f"{C.BRIGHT_RED}[✗]{C.RESET}",
        "action": f"{C.BRIGHT_MAGENTA}[➜]{C.RESET}"
    }
    prefix = symbols.get(kind, f"{C.GRAY}[*]{C.RESET}")
    print(f"{prefix} {msg}")