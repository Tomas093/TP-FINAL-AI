# =============================================================================
# Cell 04 — State: TaskState
# =============================================================================
# The TaskState class tracks the full lifecycle of a single agent task:
# plan, status, observations, errors, sources consulted, files modified,
# subagent results, and action history (with MD5 hashing for loop detection).
# to_summary() provides an aggressively truncated view for LLM context.
# =============================================================================

import hashlib
import json


class TaskState:
    """
    Mutable state object for a single agent task.

    Tracks everything the orchestrator and subagents need to know about
    the current task: plan steps, progress, observations, errors, sources,
    file modifications, and action history.
    """

    # Valid status transitions
    VALID_STATUSES = (
        "planning", "exploring", "researching", "implementing",
        "testing", "reviewing", "done", "blocked",
    )

    def __init__(self, original_request: str):
        """
        Initialize a new TaskState.

        Args:
            original_request: The user's original task description.
        """
        self.original_request: str = original_request
        self.status: str = "planning"
        self.plan: list = []
        self.current_step: int = 0
        self.subagent_results: dict = {}       # {agent_name: [result_strings]}
        self.sources_consulted: list = []      # [{"type": str, "ref": str, "snippet": str}]
        self.files_modified: list = []
        self.observations: list = []
        self.errors: list = []
        self.iteration_count: int = 0
        self.action_history: list = []         # [{"action": str, "args_hash": str, "result_hash": str}]

    def add_source(self, source_type: str, ref: str, snippet: str):
        """
        Record a consulted source (RAG, web, repo, or memory).

        Args:
            source_type: One of "rag", "web", "repo", "memory".
            ref: Reference identifier (URL, file path, collection name, etc.).
            snippet: A short excerpt from the source.
        """
        self.sources_consulted.append({
            "type": source_type,
            "ref": ref,
            "snippet": snippet[:200],  # Cap snippet length at storage time
        })

    def add_observation(self, text: str):
        """
        Record an observation made during task execution.

        Args:
            text: The observation text.
        """
        self.observations.append(text)

    def mark_file_modified(self, path: str):
        """
        Record that a file was modified.

        Args:
            path: The path to the modified file.
        """
        if path not in self.files_modified:
            self.files_modified.append(path)

    def add_error(self, error: str):
        """
        Record an error encountered during execution.

        Args:
            error: The error message or description.
        """
        self.errors.append(error)

    def record_action(self, action: str, args: str, result: str):
        """
        Record an action for loop detection purposes.

        Uses MD5 hashing on args and result to enable efficient comparison
        without storing full content.

        Args:
            action: The action/tool name.
            args: The arguments (as a string).
            result: The result (as a string).
        """
        args_hash = hashlib.md5(args.encode("utf-8", errors="replace")).hexdigest()
        result_hash = hashlib.md5(result.encode("utf-8", errors="replace")).hexdigest()
        self.action_history.append({
            "action": action,
            "args_hash": args_hash,
            "result_hash": result_hash,
        })

    def to_summary(self) -> str:
        """
        Generate a COMPACT summary suitable for LLM context injection.

        Aggressively truncates to stay under ~1500 characters:
        - Only the last 5 observations
        - Only the last 5 errors
        - Source snippets capped at 100 chars each
        - Plan steps shown concisely

        Returns:
            A truncated string summary of the current task state.
        """
        parts: list = []

        # Header
        parts.append(f"[Task] {self.original_request[:120]}")
        parts.append(f"[Status] {self.status} | Step {self.current_step}/{len(self.plan)} | Iter {self.iteration_count}")

        # Plan (compact)
        if self.plan:
            plan_lines = []
            for i, step in enumerate(self.plan):
                marker = "→" if i == self.current_step else "·"
                step_text = step[:60] if isinstance(step, str) else str(step)[:60]
                plan_lines.append(f"  {marker} {i}: {step_text}")
            parts.append("[Plan]\n" + "\n".join(plan_lines))

        # Subagent results (just names and count)
        if self.subagent_results:
            agent_summary = ", ".join(
                f"{name}({len(results)})" for name, results in self.subagent_results.items()
            )
            parts.append(f"[Subagents] {agent_summary}")

        # Sources (truncated snippets)
        if self.sources_consulted:
            src_lines = []
            for src in self.sources_consulted[-5:]:  # Last 5 sources
                snippet = src.get("snippet", "")[:100]
                src_lines.append(f"  [{src['type']}] {src['ref']}: {snippet}")
            parts.append("[Sources]\n" + "\n".join(src_lines))

        # Files modified
        if self.files_modified:
            parts.append(f"[Files Modified] {', '.join(self.files_modified[-10:])}")

        # Observations (last 5, truncated)
        if self.observations:
            obs_lines = [f"  - {obs[:100]}" for obs in self.observations[-5:]]
            parts.append("[Observations]\n" + "\n".join(obs_lines))

        # Errors (last 5, truncated)
        if self.errors:
            err_lines = [f"  ❌ {err[:100]}" for err in self.errors[-5:]]
            parts.append("[Errors]\n" + "\n".join(err_lines))

        summary = "\n".join(parts)

        # Final hard truncation to ensure we stay under 1500 chars
        if len(summary) > 1500:
            summary = summary[:1497] + "..."

        return summary



# --- Confirmation ---
print("=" * 60)
print("✅ TaskState definido correctamente")
print("   Propiedades: original_request, status, plan, current_step,")
print("   subagent_results, sources_consulted, files_modified,")
print("   observations, errors, iteration_count, action_history")
print("   Métodos: add_source, add_observation, mark_file_modified,")
print("   add_error, record_action, to_summary")
print("=" * 60)
