# =============================================================================
# Cell 03 — Observability: Langfuse Tracer
# =============================================================================
# Provides the Tracer class that logs LLM generations, tool calls, and RAG
# retrievals to Langfuse for monitoring and debugging. Gracefully degrades
# if Langfuse credentials are not configured.
# =============================================================================

import time
from langfuse import Langfuse
from google.colab import userdata

# --- Attempt to load Langfuse credentials ---
_LANGFUSE_PUBLIC_KEY: str = ""
_LANGFUSE_SECRET_KEY: str = ""
_LANGFUSE_HOST: str = "https://cloud.langfuse.com"

try:
    _LANGFUSE_PUBLIC_KEY = userdata.get("LANGFUSE_PUBLIC_KEY")
    _LANGFUSE_SECRET_KEY = userdata.get("LANGFUSE_SECRET_KEY")
except Exception:
    # Keys not configured — Tracer will run in disabled mode
    pass

# Optionally override host
try:
    _host = userdata.get("LANGFUSE_HOST")
    if _host:
        _LANGFUSE_HOST = _host
except Exception:
    pass


class Tracer:
    """
    Observability wrapper around Langfuse for tracing LLM calls,
    tool executions, and RAG retrievals.

    If Langfuse credentials are not available, all methods become
    no-ops to avoid crashing the notebook.
    """

    def __init__(self):
        """Initialize the Langfuse client if credentials are available."""
        self.enabled: bool = False
        self.client = None

        if _LANGFUSE_PUBLIC_KEY and _LANGFUSE_SECRET_KEY:
            try:
                self.client = Langfuse(
                    public_key=_LANGFUSE_PUBLIC_KEY,
                    secret_key=_LANGFUSE_SECRET_KEY,
                    host=_LANGFUSE_HOST,
                )
                self.enabled = True
            except Exception as e:
                print(f"⚠️  No se pudo inicializar Langfuse: {e}")
                self.enabled = False

    def start_trace(self, name: str, user_id: str = "user"):
        """
        Start a new Langfuse trace.

        Args:
            name: Name/identifier for this trace (e.g., the task description).
            user_id: User identifier for grouping traces.

        Returns:
            A Langfuse trace object, or None if disabled.
        """
        if not self.enabled:
            return None
        try:
            trace = self.client.trace(
                name=name,
                user_id=user_id,
            )
            return trace
        except Exception as e:
            print(f"⚠️  Error al crear trace: {e}")
            return None

    def log_llm_call(
        self,
        trace,
        agent_name: str,
        messages: list,
        response,
        duration_ms: float,
    ):
        """
        Log an LLM generation to Langfuse.

        Records the model used, input/output messages, token usage,
        estimated cost, and latency.

        Args:
            trace: The parent Langfuse trace object.
            agent_name: Name of the agent making the call.
            messages: The input messages sent to the LLM.
            response: The OpenAI API response object.
            duration_ms: Wall-clock duration of the call in milliseconds.
        """
        if not self.enabled or trace is None:
            return
        try:
            # Extract token usage from the response
            usage = response.usage if response and hasattr(response, "usage") else None
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            # Rough cost estimate (USD) for gpt-5-nano
            # Approximation: $0.10/1M input tokens, $0.40/1M output tokens
            estimated_cost = (prompt_tokens * 0.10 / 1_000_000) + \
                             (completion_tokens * 0.40 / 1_000_000)

            # Extract the output text
            output_text = ""
            if response and response.choices:
                choice = response.choices[0]
                if hasattr(choice.message, "content") and choice.message.content:
                    output_text = choice.message.content

            trace.generation(
                name=f"llm-{agent_name}",
                model=MODEL,
                input=messages,
                output=output_text,
                usage={
                    "promptTokens": prompt_tokens,
                    "completionTokens": completion_tokens,
                    "totalTokens": total_tokens,
                },
                metadata={
                    "agent": agent_name,
                    "duration_ms": round(duration_ms, 2),
                    "estimated_cost_usd": round(estimated_cost, 6),
                },
            )
        except Exception as e:
            print(f"⚠️  Error al registrar llamada LLM: {e}")

    def log_tool_call(
        self,
        trace,
        tool_name: str,
        args: dict,
        result: str,
        duration_ms: float,
    ):
        """
        Log a tool execution as a Langfuse span.

        Args:
            trace: The parent Langfuse trace object.
            tool_name: Name of the tool executed.
            args: Arguments passed to the tool.
            result: The tool's return value (as string).
            duration_ms: Duration of the tool call in milliseconds.
        """
        if not self.enabled or trace is None:
            return
        try:
            trace.span(
                name=f"tool-{tool_name}",
                input=args,
                output=result[:2000] if result else "",  # Truncate long results
                metadata={
                    "tool": tool_name,
                    "duration_ms": round(duration_ms, 2),
                },
            )
        except Exception as e:
            print(f"⚠️  Error al registrar llamada de herramienta: {e}")

    def log_rag_retrieval(self, trace, query: str, results: list):
        """
        Log a RAG retrieval operation as a Langfuse span.

        Args:
            trace: The parent Langfuse trace object.
            query: The search query used.
            results: List of retrieved documents/chunks.
        """
        if not self.enabled or trace is None:
            return
        try:
            trace.span(
                name="rag-retrieval",
                input={"query": query},
                output={"num_results": len(results), "results": results[:10]},
                metadata={
                    "query_length": len(query),
                    "num_results": len(results),
                },
            )
        except Exception as e:
            print(f"⚠️  Error al registrar búsqueda RAG: {e}")

    def flush(self):
        """Flush all pending events to Langfuse."""
        if not self.enabled or self.client is None:
            return
        try:
            self.client.flush()
        except Exception as e:
            print(f"⚠️  Error al hacer flush de Langfuse: {e}")


# --- Global Tracer instance ---
tracer: Tracer = Tracer()

# --- Status message ---
print("=" * 60)
if tracer.enabled:
    print("✅ Langfuse Tracer inicializado correctamente")
    print(f"   Host: {_LANGFUSE_HOST}")
else:
    print("⚠️  Langfuse Tracer en modo deshabilitado (claves no configuradas)")
    print("   El agente funcionará normalmente sin observabilidad.")
print("=" * 60)
