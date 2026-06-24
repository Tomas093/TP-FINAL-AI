# ── Cell 08: Context Management & Loop Detection ────────────────────────────────
# Uses globals from prior cells: client, MODEL

import hashlib


class ContextManager:
    """Manages conversation context length by estimating tokens and summarizing
    older messages when the context approaches its limit."""

    def __init__(self, max_tokens: int = 20000):
        self.max_tokens = max_tokens

    def estimate_tokens(self, messages: list) -> int:
        """Rough estimate: 1 token ≈ 4 characters."""
        total_chars = 0
        for msg in messages:
            content = msg.get("content") or ""
            total_chars += len(content)
        return total_chars // 4

    def should_summarize(self, messages: list) -> bool:
        """True if estimated tokens exceed 70 % of max_tokens."""
        return self.estimate_tokens(messages) > int(self.max_tokens * 0.7)

    def summarize_history(self, messages: list) -> list:
        """Summarize older messages via the LLM, keeping the system prompt and
        the last 6 messages intact.

        Returns a new messages list with the middle section replaced by a
        summary injected as a system message.
        """
        if len(messages) <= 7:
            # Nothing meaningful to summarize (system + ≤6 messages)
            return messages

        system_msg = messages[0]
        last_6 = messages[-6:]
        middle = messages[1:-6]

        if not middle:
            return messages

        # Build a summary request for the middle messages
        middle_text = "\n".join(
            f"[{m.get('role', '?')}]: {(m.get('content') or '')[:300]}"
            for m in middle
        )

        try:
            summary_response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Summarize this conversation concisely, preserving "
                            "key decisions, file changes, and errors."
                        ),
                    },
                    {"role": "user", "content": middle_text},
                ],
                max_tokens=500,
            )
            summary_text = summary_response.choices[0].message.content or ""
        except Exception as e:
            summary_text = f"(Error al resumir: {e})"

        summary_msg = {
            "role": "system",
            "content": f"Previous conversation summary: {summary_text}",
        }

        return [system_msg, summary_msg] + last_6


class LoopDetector:
    """Detects when a subagent repeats the same action+args+result too many times."""

    def __init__(self, max_repeats: int = 3):
        self.max_repeats = max_repeats
        self.history: list = []  # list of (action, args_hash, result_hash)

    def record(self, action: str, args_hash: str, result_hash: str):
        """Record an action for loop detection."""
        self.history.append((action, args_hash, result_hash))

    def check(self) -> str | None:
        """Check for loops at the tail of the history.

        Returns a warning string if the last *max_repeats* entries are identical,
        otherwise returns None.
        """
        if len(self.history) < self.max_repeats:
            return None

        tail = self.history[-self.max_repeats:]
        if len(set(tail)) == 1:
            action, _, _ = tail[0]
            return (
                f"⚠️ Loop detectado: la acción '{action}' se repitió "
                f"{self.max_repeats} veces con los mismos argumentos y resultado. "
                f"Intentá un enfoque diferente."
            )
        return None

    def reset(self):
        """Clear history."""
        self.history.clear()


# ── Confirmation ─────────────────────────────────────────────────────────────────
print("🧠 ContextManager y LoopDetector listos.")
