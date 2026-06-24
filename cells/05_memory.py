# =============================================================================
# Cell 05 — Memory: ProjectMemory
# =============================================================================
# Persistent project memory backed by JSON files. Stores architectural
# knowledge, important files, dependencies, useful commands, conventions,
# decisions, bugs, and session summaries across agent sessions.
# get_context_summary() produces a compact string (< 800 chars) suitable
# for injection into LLM system prompts.
# =============================================================================

import json
import os


class ProjectMemory:
    """
    Persistent memory store for a project.

    Remembers architectural decisions, important files, dependencies,
    useful commands, coding conventions, bugs found, and session summaries.
    Data is serialized to/from JSON on disk.
    """

    # Default empty memory structure
    _DEFAULT_DATA = {
        "architecture": "",
        "important_files": {},    # {path: description}
        "dependencies": [],       # [dependency strings]
        "commands": {},           # {name: command_string}
        "conventions": [],        # [convention strings]
        "decisions": [],          # [decision strings]
        "bugs": [],               # [bug description strings]
        "session_summaries": [],  # [summary strings]
    }

    def __init__(self, project_name: str, base_dir: str = "./data/memory"):
        """
        Initialize project memory.

        Args:
            project_name: Identifier for the project (used as filename).
            base_dir: Directory where memory JSON files are stored.
        """
        self.project_name: str = project_name
        self.base_dir: str = base_dir
        # Deep copy the default data structure
        self.data: dict = json.loads(json.dumps(self._DEFAULT_DATA))

    @property
    def _file_path(self) -> str:
        """Full path to the memory JSON file."""
        return os.path.join(self.base_dir, f"{self.project_name}.json")

    def load(self):
        """
        Load memory from JSON file if it exists.

        Merges loaded data with defaults to ensure all keys are present
        even if the file was saved with an older schema.
        """
        try:
            if os.path.exists(self._file_path):
                with open(self._file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Merge with defaults (preserves new keys added to schema)
                for key, default_value in self._DEFAULT_DATA.items():
                    if key not in loaded:
                        loaded[key] = (
                            json.loads(json.dumps(default_value))
                            if isinstance(default_value, (dict, list))
                            else default_value
                        )
                self.data = loaded
        except Exception as e:
            print(f"⚠️  Error al cargar memoria del proyecto: {e}")

    def save(self):
        """
        Save memory to JSON file, creating directories as needed.
        """
        try:
            os.makedirs(self.base_dir, exist_ok=True)
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Error al guardar memoria del proyecto: {e}")

    def update(self, section: str, data):
        """
        Update a section of memory by merging new data.

        Behavior depends on the section's data type:
        - str: replaces the value
        - dict: merges keys (update)
        - list: appends items (avoids duplicates for simple values)

        Args:
            section: The memory section key to update.
            data: The new data to merge into the section.
        """
        if section not in self.data:
            print(f"⚠️  Sección desconocida: '{section}'")
            return

        current = self.data[section]

        if isinstance(current, str):
            # For strings, just replace
            self.data[section] = str(data)

        elif isinstance(current, dict) and isinstance(data, dict):
            # For dicts, merge
            current.update(data)

        elif isinstance(current, list):
            # For lists, append new items
            if isinstance(data, list):
                for item in data:
                    if item not in current:
                        current.append(item)
            else:
                if data not in current:
                    current.append(data)

        else:
            # Fallback: just replace
            self.data[section] = data

    def get_context_summary(self) -> str:
        """
        Generate a compact summary (< 800 chars) for LLM system prompts.

        Includes architecture overview, key files, useful commands,
        and recent decisions. Designed to give the agent quick context
        about the project without consuming too many tokens.

        Returns:
            A compact string summary of project memory.
        """
        parts: list = []

        # Architecture (truncated)
        arch = self.data.get("architecture", "")
        if arch:
            parts.append(f"[Arch] {arch[:150]}")

        # Important files (top 5)
        files = self.data.get("important_files", {})
        if files:
            file_entries = list(files.items())[:5]
            file_lines = [f"  {path}: {desc[:40]}" for path, desc in file_entries]
            parts.append("[Key Files]\n" + "\n".join(file_lines))

        # Commands (top 4)
        commands = self.data.get("commands", {})
        if commands:
            cmd_entries = list(commands.items())[:4]
            cmd_lines = [f"  {name}: {cmd[:50]}" for name, cmd in cmd_entries]
            parts.append("[Commands]\n" + "\n".join(cmd_lines))

        # Recent decisions (last 3)
        decisions = self.data.get("decisions", [])
        if decisions:
            dec_lines = [f"  - {d[:60]}" for d in decisions[-3:]]
            parts.append("[Decisions]\n" + "\n".join(dec_lines))

        # Conventions (top 3)
        conventions = self.data.get("conventions", [])
        if conventions:
            conv_lines = [f"  - {c[:50]}" for c in conventions[:3]]
            parts.append("[Conventions]\n" + "\n".join(conv_lines))

        # Dependencies count
        deps = self.data.get("dependencies", [])
        if deps:
            parts.append(f"[Deps] {len(deps)} dependencies")

        summary = "\n".join(parts)

        # Hard truncation to stay under 800 chars
        if len(summary) > 800:
            summary = summary[:797] + "..."

        return summary if summary else "[No project memory available]"


# --- Confirmation ---
print("=" * 60)
print("✅ ProjectMemory definido correctamente")
print("   Secciones: architecture, important_files, dependencies,")
print("   commands, conventions, decisions, bugs, session_summaries")
print("   Métodos: load, save, update, get_context_summary")
print("   Persistencia: JSON en ./data/memory/<project_name>.json")
print("=" * 60)
