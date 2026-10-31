import os
import shutil
import json
import math
import re
import hashlib
import time
import requests
from dotenv import load_dotenv
from keys import get_keys, reload_env

reload_env()

# Base storage directory for all projects
RAG_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_storage")

SUPPORTED_EXTENSIONS = {
    ".py", ".md", ".txt", ".yaml", ".yml", ".json", ".js", ".ts",
    ".html", ".css", ".sql", ".sh", ".ps1", ".env.example", ".csv"
}

IGNORED_DIRS = {
    "venv", ".git", "__pycache__", "rag_storage", "node_modules",
    ".idea", ".vscode", "dist", "build", ".pytest_cache"
}

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
    "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more",
    "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they",
    "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves"
}

class PriorityRAGManager:
    """
    Priority-Driven Context & RAG Engine:
    - Priority 1: rules.md     (Highest Priority - Golden Rules & Hard Constraints)
    - Priority 2: notes.md     (Medium Priority  - Developer Memory & Explicit Facts)
    - Priority 3: knowledge.md (General Context   - Codebase Excerpts & Documentation)
    """
    def __init__(self, base_dir=RAG_BASE_DIR, default_project="default"):
        self.base_dir = base_dir
        self.project = default_project
        self.enabled = True
        self._ensure_storage()

    def set_project(self, project_name):
        cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '_', project_name.strip())
        if not cleaned:
            cleaned = "default"
        self.project = cleaned
        self._ensure_storage()
        return self.project

    def get_project_dir(self):
        return os.path.join(self.base_dir, self.project)

    def _ensure_storage(self):
        project_dir = self.get_project_dir()
        os.makedirs(project_dir, exist_ok=True)

        rules_file = os.path.join(project_dir, "rules.md")
        notes_file = os.path.join(project_dir, "notes.md")
        kb_file = os.path.join(project_dir, "knowledge_base.md")
        index_file = os.path.join(project_dir, "knowledge.json")
        cache_file = os.path.join(project_dir, "cache.json")

        if not os.path.exists(rules_file):
            with open(rules_file, "w", encoding="utf-8") as f:
                f.write(f"# Project Rules: {self.project}\n\n*Highest priority golden rules, constraints, and non-negotiable guidelines.*\n\n")
        if not os.path.exists(notes_file):
            with open(notes_file, "w", encoding="utf-8") as f:
                f.write(f"# Project Notes: {self.project}\n\n*Developer notes, architectural decisions, and explicit facts.*\n\n")
        if not os.path.exists(kb_file):
            with open(kb_file, "w", encoding="utf-8") as f:
                f.write(f"# Project Knowledge Base: {self.project}\n\n*Codebase and documentation index.*\n\n")
        if not os.path.exists(index_file):
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump([], f)
        if not os.path.exists(cache_file):
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load_chunks(self):
        path = os.path.join(self.get_project_dir(), "knowledge.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_chunks(self, chunks):
        path = os.path.join(self.get_project_dir(), "knowledge.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2)
        self._sync_markdown_knowledge_base(chunks)

    def _load_cache(self):
        path = os.path.join(self.get_project_dir(), "cache.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cache(self, cache):
        path = os.path.join(self.get_project_dir(), "cache.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)

    # -------------------------------------------------------------
    # PRIORITY 1: RULES MANAGEMENT (rules.md)
    # -------------------------------------------------------------
    def add_rule(self, rule_text):
        rules_path = os.path.join(self.get_project_dir(), "rules.md")
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        clean_text = rule_text.strip()
        with open(rules_path, "a", encoding="utf-8") as f:
            f.write(f"- [{timestamp}] {clean_text}\n")
        return f"Rule added to project '{self.project}'."

    def get_rules_content(self):
        rules_path = os.path.join(self.get_project_dir(), "rules.md")
        if os.path.exists(rules_path):
            with open(rules_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def get_rules_list(self):
        content = self.get_rules_content()
        rules = []
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("-"):
                cleaned = re.sub(r'^-\s*(\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\]\s*)?', '', line_str)
                if cleaned:
                    rules.append(cleaned)
        return rules

    # -------------------------------------------------------------
    # PRIORITY 2: NOTES MANAGEMENT (notes.md)
    # -------------------------------------------------------------
    def add_note(self, title, content):
        notes_path = os.path.join(self.get_project_dir(), "notes.md")
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        title_clean = title.strip()
        content_clean = content.strip()

        note_entry = (
            f"\n## {title_clean}\n"
            f"*Recorded: {timestamp}*\n\n"
            f"{content_clean}\n\n---\n"
        )
        with open(notes_path, "a", encoding="utf-8") as f:
            f.write(note_entry)

        composite_text = f"Title: {title_clean}\nTopic: {title_clean}\nContent:\n{content_clean}"
        count = self.add_document(f"notes.md#{title_clean}", composite_text, is_note=True)
        return count

    def get_notes_content(self):
        notes_path = os.path.join(self.get_project_dir(), "notes.md")
        if os.path.exists(notes_path):
            with open(notes_path, "r", encoding="utf-8") as f:
                return f.read()
        return "No notes found."

    # -------------------------------------------------------------
    # PRIORITY 3: KNOWLEDGE BASE SYNC (knowledge_base.md)
    # -------------------------------------------------------------
    def _sync_markdown_knowledge_base(self, chunks):
        path = os.path.join(self.get_project_dir(), "knowledge_base.md")
        grouped = {}
        for c in chunks:
            src = c.get("source", "General")
            grouped.setdefault(src, []).append(c)

        lines = [
            f"# Project Knowledge Base: {self.project}",
            f"*Last Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}* | Total Chunks: {len(chunks)}",
            "",
            "## Table of Contents"
        ]
        for src in grouped:
            anchor = re.sub(r'[^a-zA-Z0-9_\-]', '', src.lower().replace('.', ''))
            lines.append(f"- [{src}](#{anchor}) ({len(grouped[src])} chunks)")

        lines.append("\n---\n")

        for src, src_chunks in grouped.items():
            lines.append(f"## {src}")
            for item in src_chunks:
                header = item.get("breadcrumb", "")
                text = item.get("text", "")
                chunk_id = item.get("id", "")
                lines.append(f"### {header or 'Chunk'} `[{chunk_id}]`\n{text}\n")
            lines.append("---\n")

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception:
            pass

    # -------------------------------------------------------------
    # Substantive Document Chunking
    # -------------------------------------------------------------
    def chunk_document(self, text, source_name="", max_chars=900, overlap=150):
        """
        Intelligently chunks code and markdown:
        - Markdown files: Splits on real headings (# Title, ## Section) avoiding comment dividers.
        - Code files: Splits on class / def / async def, keeping small helper functions together.
        - Drops or merges trivial comment lines to guarantee high-value, substantive chunks.
        """
        is_code = any(source_name.lower().endswith(ext) for ext in [".py", ".js", ".ts", ".sh", ".ps1", ".sql", ".yaml", ".json"])
        lines = text.splitlines(keepends=True)
        sections = []
        current_breadcrumb = source_name
        current_buffer = []

        if is_code:
            # Code boundary pattern: class, def, async def
            split_pattern = re.compile(r'^(class\s+[a-zA-Z0-9_]+|def\s+[a-zA-Z0-9_]+|async\s+def\s+[a-zA-Z0-9_]+)')
        else:
            # Markdown boundary pattern: heading with alphanumeric title
            split_pattern = re.compile(r'^(#{1,4}\s+[a-zA-Z0-9_\`\*])')

        for line in lines:
            line_str = line.strip()
            # Only trigger split if the accumulated buffer is at least 250 chars
            if split_pattern.match(line_str) and sum(len(l) for l in current_buffer) >= 250:
                sec_text = "".join(current_buffer).strip()
                if len(sec_text) >= 60:
                    sections.append((current_breadcrumb, sec_text))
                current_buffer = []
                current_breadcrumb = f"{source_name} > {line_str[:40]}"
            current_buffer.append(line)

        if current_buffer:
            sec_text = "".join(current_buffer).strip()
            if len(sec_text) >= 60:
                sections.append((current_breadcrumb, sec_text))
            elif sections:
                # Merge small trailing buffer into previous section
                prev_b, prev_t = sections.pop()
                sections.append((prev_b, prev_t + "\n" + sec_text))

        final_chunks = []
        for breadcrumb, sec_text in sections:
            # Skip chunks that are purely comment divider lines
            clean_content = re.sub(r'[\s\-\=\#\*\_\/\\]', '', sec_text)
            if len(clean_content) < 30:
                continue

            if len(sec_text) <= max_chars:
                final_chunks.append({"breadcrumb": breadcrumb, "text": sec_text})
            else:
                start = 0
                while start < len(sec_text):
                    end = min(start + max_chars, len(sec_text))
                    if end < len(sec_text):
                        split_at = sec_text.rfind("\n", start, end)
                        if split_at == -1 or split_at < start + (max_chars // 2):
                            split_at = sec_text.rfind(". ", start, end)
                        if split_at != -1 and split_at > start + (max_chars // 2):
                            end = split_at + 1
                    chunk_body = sec_text[start:end].strip()
                    if len(re.sub(r'[\s\-\=\#\*\_\/\\]', '', chunk_body)) >= 30:
                        final_chunks.append({"breadcrumb": breadcrumb, "text": chunk_body})
                    start += max(max_chars - overlap, 50)

        return final_chunks

    # -------------------------------------------------------------
    # Tokenizer & Hybrid Embedding Engine
    # -------------------------------------------------------------
    def _extract_keywords(self, text):
        words = re.findall(r'\b[a-zA-Z0-9_\.\-]{2,}\b', text.lower())
        return [w for w in words if w not in STOP_WORDS]

    def _lexical_vector(self, text):
        keywords = self._extract_keywords(text)
        vec = {}
        for w in keywords:
            vec[w] = vec.get(w, 0) + 1
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm > 0:
            for k in vec:
                vec[k] /= norm
        return vec

    def get_dense_embedding(self, text):
        keys = get_keys("gemini")
        if not keys:
            return None
        # Try primary key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={keys[0]}"
        payload = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text[:2048]}]}
        }
        try:
            resp = requests.post(url, json=payload, timeout=6)
            if resp.status_code == 200:
                values = resp.json().get("embedding", {}).get("values")
                if values and isinstance(values, list):
                    return values
        except Exception:
            pass
        return None

    def _cosine_dense(self, v1, v2):
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(b * b for b in v2))
        return dot / (n1 * n2) if (n1 * n2) > 0 else 0.0

    def _cosine_sparse(self, d1, d2):
        if not d1 or not d2:
            return 0.0
        common = set(d1.keys()) & set(d2.keys())
        return sum(d1[k] * d2[k] for k in common)

    # -------------------------------------------------------------
    # Document Ingestion & CWD Context Update
    # -------------------------------------------------------------
    def add_document(self, source_name, content, is_note=False):
        raw_chunks = self.chunk_document(content, source_name=source_name)
        if not raw_chunks:
            return 0

        existing_chunks = self._load_chunks()
        new_records = []

        for i, c in enumerate(raw_chunks):
            chunk_text = c["text"]
            breadcrumb = c.get("breadcrumb", source_name)
            searchable_text = f"{breadcrumb}\n{chunk_text}"

            dense_vec = self.get_dense_embedding(searchable_text)
            sparse_vec = self._lexical_vector(searchable_text)
            chunk_hash = hashlib.md5(f"{source_name}_{i}_{chunk_text[:30]}".encode()).hexdigest()[:10]

            new_records.append({
                "id": chunk_hash,
                "source": source_name,
                "breadcrumb": breadcrumb,
                "text": chunk_text,
                "dense_vector": dense_vec,
                "sparse_vector": sparse_vec,
                "is_note": is_note
            })

        clean_chunks = [ch for ch in existing_chunks if ch.get("source") != source_name]
        clean_chunks.extend(new_records)
        self._save_chunks(clean_chunks)
        return len(new_records)

    def add_file(self, filepath):
        if not os.path.exists(filepath):
            return False, f"File not found: {filepath}"
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            source = os.path.basename(filepath)
            count = self.add_document(source, content)
            return True, f"Indexed {count} substantive chunk(s) from '{source}' into project '{self.project}'."
        except Exception as e:
            return False, f"Error indexing file: {e}"

    def add_directory(self, dirpath):
        if not os.path.isdir(dirpath):
            return False, f"Directory not found: {dirpath}"

        indexed_files = 0
        total_chunks = 0

        for root, dirs, files in os.walk(dirpath):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith('.')]
            for f in files:
                _, ext = os.path.splitext(f)
                if ext.lower() in SUPPORTED_EXTENSIONS and not f.startswith('.'):
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, dirpath)
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="ignore") as fh:
                            content = fh.read()
                        if content.strip():
                            count = self.add_document(rel_p, content)
                            if count > 0:
                                indexed_files += 1
                                total_chunks += count
                    except Exception:
                        continue

        return True, f"Indexed {indexed_files} file(s) ({total_chunks} chunks) from '{dirpath}' into project '{self.project}'."

    def update_context(self, target_path=None):
        """
        Updates context from target_path if provided, otherwise from os.getcwd().
        Supports directories or single files.
        Re-indexes code and documentation files, syncing knowledge_base.md and purging cache.
        """
        if not target_path or not str(target_path).strip():
            target_path = os.getcwd()
        else:
            target_path = os.path.abspath(str(target_path).strip().strip('"').strip("'"))

        if not os.path.exists(target_path):
            return False, f"Path not found: '{target_path}'"

        if os.path.isdir(target_path):
            success, msg = self.add_directory(target_path)
        else:
            success, msg = self.add_file(target_path)

        if success:
            self._save_cache({})

        return success, f"Context updated from '{target_path}':\n  {msg}"

    def update_context_from_cwd(self):
        """Backward-compatible alias for update_context(None)."""
        return self.update_context(None)

    # -------------------------------------------------------------
    # Search Engine
    # -------------------------------------------------------------
    def search_context(self, query, top_k=4, min_score=0.10):
        chunks = self._load_chunks()
        if not chunks:
            return []

        query_dense = self.get_dense_embedding(query)
        query_sparse = self._lexical_vector(query)
        query_keywords = set(self._extract_keywords(query))

        scored = []
        for ch in chunks:
            dense_score = 0.0
            if query_dense and ch.get("dense_vector"):
                dense_score = self._cosine_dense(query_dense, ch["dense_vector"])

            sparse_score = self._cosine_sparse(query_sparse, ch.get("sparse_vector", {}))

            content_lower = f"{ch.get('breadcrumb', '')} {ch.get('text', '')}".lower()
            contained_matches = sum(1 for kw in query_keywords if kw in content_lower)
            containment_boost = 0.18 * (contained_matches / len(query_keywords)) if query_keywords else 0.0
            note_boost = 0.12 if ch.get("is_note") else 0.0

            if query_dense and ch.get("dense_vector"):
                final_score = (dense_score * 0.55) + (sparse_score * 0.30) + containment_boost + note_boost
            else:
                final_score = (sparse_score * 0.70) + containment_boost + note_boost

            if final_score >= min_score or contained_matches > 0:
                scored.append((final_score, ch))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    # -------------------------------------------------------------
    # Priority Augmented Prompt
    # -------------------------------------------------------------
    def build_priority_augmented_prompt(self, user_prompt, max_knowledge_chunks=3):
        if not self.enabled:
            return user_prompt, {"rules": 0, "notes": 0, "knowledge": 0}

        stats = {"rules": 0, "notes": 0, "knowledge": 0}

        # 1. Rules
        rules_list = self.get_rules_list()
        rules_block = ""
        if rules_list:
            rules_formatted = "\n".join([f"- {r}" for r in rules_list])
            rules_block = (
                f"### [PRIORITY 1: PROJECT RULES (rules.md)]\n"
                f"These are STRICT, non-negotiable project policies:\n"
                f"{rules_formatted}\n\n"
            )
            stats["rules"] = len(rules_list)

        # 2. Notes & Knowledge Chunks
        search_results = self.search_context(user_prompt, top_k=max_knowledge_chunks + 3)

        notes_chunks = []
        knowledge_chunks = []

        for score, ch in search_results:
            if ch.get("is_note") or "notes.md" in ch.get("source", ""):
                notes_chunks.append((score, ch))
            else:
                if len(knowledge_chunks) < max_knowledge_chunks:
                    knowledge_chunks.append((score, ch))

        notes_block = ""
        if notes_chunks:
            sections = []
            for score, ch in notes_chunks:
                src = ch.get("breadcrumb") or ch.get("source")
                sections.append(f"#### Note [{src}] (Relevance: {score:.2f})\n{ch.get('text')}")
            notes_block = (
                f"### [PRIORITY 2: DEVELOPER NOTES (notes.md)]\n"
                f"Verified developer notes and explicit facts:\n"
                + "\n\n".join(sections)
                + "\n\n"
            )
            stats["notes"] = len(notes_chunks)

        kb_block = ""
        if knowledge_chunks:
            sections = []
            for score, ch in knowledge_chunks:
                src = ch.get("breadcrumb") or ch.get("source")
                sections.append(f"#### Code/Doc [{src}] (Relevance: {score:.2f})\n```\n{ch.get('text')}\n```")
            kb_block = (
                f"### [PRIORITY 3: CODEBASE CONTEXT (knowledge_base.md)]\n"
                f"Supporting codebase context:\n"
                + "\n\n".join(sections)
                + "\n\n"
            )
            stats["knowledge"] = len(knowledge_chunks)

        total_injected = stats["rules"] + stats["notes"] + stats["knowledge"]
        if total_injected == 0:
            return user_prompt, stats

        augmented_prompt = (
            f"You are working on project '{self.project}'. "
            f"Adhere strictly to the priority hierarchy below:\n"
            f"1. Rules in rules.md take precedence over everything.\n"
            f"2. Notes in notes.md take precedence over generic knowledge.\n"
            f"3. Codebase context is for reference.\n\n"
            f"--- PROJECT CONTEXT HIERARCHY ---\n"
            f"{rules_block}"
            f"{notes_block}"
            f"{kb_block}"
            f"---------------------------------\n\n"
            f"User Question: {user_prompt}"
        )
        return augmented_prompt, stats

    # -------------------------------------------------------------
    # Query Cache (Protected against Empty Responses)
    # -------------------------------------------------------------
    def get_cached_response(self, query):
        cache = self._load_cache()
        key = hashlib.md5(f"{self.project}:{query.strip().lower()}".encode()).hexdigest()
        val = cache.get(key)
        if val:
            resp = val.get("response", "").strip()
            if not resp or resp.startswith("Error:"):
                # Clean up invalid/empty cache entry
                del cache[key]
                self._save_cache(cache)
                return None
        return val

    def cache_response(self, query, response_text, provider):
        # NEVER cache empty or error responses!
        if not response_text or not response_text.strip() or response_text.startswith("Error:"):
            return

        cache = self._load_cache()
        key = hashlib.md5(f"{self.project}:{query.strip().lower()}".encode()).hexdigest()
        cache[key] = {
            "response": response_text.strip(),
            "provider": f"{provider} (Cached)",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "query": query[:120]
        }
        self._save_cache(cache)

    # -------------------------------------------------------------
    # Stats & Project Maintenance
    # -------------------------------------------------------------
    def get_stats(self):
        chunks = self._load_chunks()
        cache = self._load_cache()
        rules = self.get_rules_list()
        sources = list(set(c.get("source", "unknown") for c in chunks))
        dense_count = sum(1 for c in chunks if c.get("dense_vector"))
        notes_count = sum(1 for c in chunks if c.get("is_note"))
        return {
            "project": self.project,
            "enabled": self.enabled,
            "rules_count": len(rules),
            "notes_count": notes_count,
            "total_chunks": len(chunks),
            "dense_embeddings_count": dense_count,
            "unique_sources": sources,
            "cached_queries": len(cache),
            "storage_path": self.get_project_dir()
        }

    def clear_project(self, project_name=None):
        """
        Completely removes the project folder and all its contents from rag_storage.
        If the active project is removed, automatically resets to 'default'.
        """
        target = project_name.strip() if (project_name and project_name.strip()) else self.project
        target_dir = os.path.join(self.base_dir, target)

        if os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)

        if target == self.project:
            self.set_project("default")
            return f"Removed RAG folder and all data for '{target}'. Active project reset to 'default'."
        else:
            return f"Removed RAG folder and all data for '{target}'."

    def list_projects(self):
        if not os.path.exists(self.base_dir):
            return ["default"]
        dirs = [d for d in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, d))]
        return dirs if dirs else ["default"]

rag_engine = PriorityRAGManager()
