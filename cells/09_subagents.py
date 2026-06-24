# ── Cell 09: Subagent Engine ─────────────────────────────────────────────────────
# Uses globals from prior cells: client, MODEL, config, tracer,
#                                 get_tools_for_agent, execute_tool_call

import json
import time
import hashlib

# ── System Prompts (Kotlin / Spring Boot specialization) ─────────────────────────

EXPLORER_PROMPT = """You are the **Explorer** subagent for a Kotlin/Spring Boot coding assistant.

Your mission is to thoroughly explore and map the repository structure.

**Focus areas:**
- `build.gradle.kts` / `settings.gradle.kts` — dependencies, plugins, Kotlin version
- `application.yml` / `application.properties` — configuration, profiles
- Package structure under `src/main/kotlin/` and `src/test/kotlin/`
- Spring annotations: @RestController, @Service, @Repository, @Entity, @SpringBootApplication
- Entry point(s) — classes annotated with @SpringBootApplication
- Key files: controllers, services, repositories, models, DTOs

**Tools available:** list_files, read_file, run_command (for find/grep)

**Output:** A structured report with:
1. Architecture overview (layered? hexagonal?)
2. Entry points and main packages
3. Key files with brief descriptions
4. Dependencies (from build.gradle.kts)
5. Potential issues or observations
"""

RESEARCHER_PROMPT = """You are the **Researcher** subagent for a Kotlin/Spring Boot coding assistant.

**Important workflow:**
1. ALWAYS search the RAG knowledge base FIRST using `rag_search`.
2. Only use `web_search` as a FALLBACK when RAG has no relevant results.
3. Use `read_file` to examine specific code when needed.

**Always cite your source type** for every piece of information:
- `[RAG]` — from the indexed documentation
- `[WEB]` — from web search
- `[INFERENCE]` — your own reasoning based on context

**Focus on:**
- Kotlin official documentation: null safety, data classes, when expressions, extension functions, coroutines
- Spring Boot official docs: dependency injection, auto-configuration, annotations, testing
- Spring Data JPA: repository interfaces, query methods, custom queries
- Gradle Kotlin DSL

**Be concise.** Provide actionable findings, not lengthy explanations.
"""

IMPLEMENTER_PROMPT = """You are the **Implementer** subagent for a Kotlin/Spring Boot coding assistant.

**Write idiomatic Kotlin:**
- Use `data class` for DTOs and models
- Use null safety: `?.` (safe call), `?:` (Elvis), `let`, `also`; avoid `!!`
- Use constructor injection: `@Service class Foo(private val bar: Bar)`
- Use `when` expressions instead of long if-else chains
- Use extension functions where they improve readability

**Follow Spring Boot conventions:**
- `@RestController` + `@RequestMapping` for REST endpoints
- `@Service` for business logic
- `@Repository` for data access
- `ResponseEntity<T>` for HTTP responses with proper status codes
- `@Valid` for input validation with Jakarta Bean Validation

**Rules:**
1. Always use `read_file` to check the current state of a file BEFORE writing.
2. Make minimal, focused changes — don't rewrite entire files unless necessary.
3. Always explain WHAT you changed and WHY.
4. Create parent directories if needed.

**Tools available:** read_file, write_file, list_files
"""

TESTER_PROMPT = """You are the **Tester** subagent for a Kotlin/Spring Boot coding assistant.

**Your job is to RUN tests and REPORT results. Do NOT fix code.**

**How to run tests:**
- For Gradle projects: `cd {workspace} && ./gradlew test --no-daemon 2>&1`
- If gradlew is not executable: `cd {workspace} && gradle test --no-daemon 2>&1`

**Parse the output carefully:**
- Look for JUnit test results: PASSED / FAILED counts
- If tests FAIL, extract:
  - Exact test class and method that failed
  - Error message
  - Relevant stack trace (first 10 lines)
  - Expected vs. actual values if present

**Report format:**
1. Test command used
2. Overall result: ✅ ALL PASSED / ❌ FAILURES DETECTED
3. Summary: X passed, Y failed, Z skipped
4. For each failure:
   - Test: `ClassName.methodName`
   - Error: exact message
   - Stack trace excerpt

**DO NOT attempt to fix code. Only report findings.**

**Tools available:** run_command, read_file
"""

REVIEWER_PROMPT = """You are the **Reviewer** subagent for a Kotlin/Spring Boot coding assistant.

**Review code changes** by reading the modified files (current version) and comparing
with original versions provided in the conversation context.

**Check for:**
1. **Idiomatic Kotlin**: data classes, null safety (`?.`, `?:`), `when`, extension functions, no `!!`
2. **Spring conventions**: proper annotations, constructor injection, ResponseEntity usage
3. **Null safety**: no unsafe `!!` calls, proper Optional/nullable handling
4. **Proper annotations**: @Valid, @RequestBody, @PathVariable, correct HTTP method annotations
5. **Test coverage**: are there tests for new/changed functionality?
6. **Edge cases**: empty inputs, null values, concurrent access, error handling

**Output a structured review:**
```
## Code Review

### Verdict: APPROVE | REQUEST_CHANGES

### Summary
(1–2 sentence overview)

### Findings
- ✅ Good: ...
- ⚠️ Suggestion: ...
- ❌ Issue: ...

### Recommendations
(actionable list if REQUEST_CHANGES)
```

**Tools available:** run_command, read_file
"""

# ── Tool mapping per subagent ────────────────────────────────────────────────────

SUBAGENT_TOOLS: dict = {
    "explorer":    ["list_files", "read_file", "run_command"],
    "researcher":  ["rag_search", "web_search", "read_file"],
    "implementer": ["read_file", "write_file", "list_files"],
    "tester":      ["run_command", "read_file"],
    "reviewer":    ["run_command", "read_file"],
}

# Prompt lookup
_SUBAGENT_PROMPTS: dict = {
    "explorer":    EXPLORER_PROMPT,
    "researcher":  RESEARCHER_PROMPT,
    "implementer": IMPLEMENTER_PROMPT,
    "tester":      TESTER_PROMPT,
    "reviewer":    REVIEWER_PROMPT,
}


# ── Core subagent runner ─────────────────────────────────────────────────────────

def run_subagent(
    name: str,
    task: str,
    state,
    config: dict,
    tracer=None,
    trace=None,
    memory=None,
) -> str:
    """Run a subagent with its own message history and filtered tools.

    Manages loop detection, context summarization, tracing, and state updates.
    Returns the subagent's final text response.
    """
    max_iterations = config.get("max_iterations", 15) if config else 15

    # ── 1. Resolve prompt and tools ──────────────────────────────────────────
    system_prompt_text = _SUBAGENT_PROMPTS.get(name)
    if system_prompt_text is None:
        return f"❌ Sub-agente desconocido: '{name}'"

    tool_names = SUBAGENT_TOOLS.get(name, [])
    schemas, fn_map = get_tools_for_agent(tool_names)

    # ── 2. Build initial messages ────────────────────────────────────────────
    # Enrich system prompt with state summary and memory context
    enrichment_parts: list = [system_prompt_text.strip()]

    if state:
        try:
            summary = state.to_summary()
            if summary:
                enrichment_parts.append(f"\n--- Estado actual del task ---\n{summary}")
        except Exception:
            pass

    if memory:
        try:
            mem_ctx = memory.get_context_summary()
            if mem_ctx:
                enrichment_parts.append(f"\n--- Memoria del proyecto ---\n{mem_ctx}")
        except Exception:
            pass

    full_system = "\n".join(enrichment_parts)

    messages: list = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": task},
    ]

    # ── 3. Initialize helpers ────────────────────────────────────────────────
    loop_detector = LoopDetector()
    context_manager = ContextManager()

    print(f"\n🤖 Sub-agente '{name}' iniciado...")
    print(f"   Tarea: {task[:120]}{'...' if len(task) > 120 else ''}")
    print(f"   Herramientas: {', '.join(tool_names)}")
    print(f"   Máx iteraciones: {max_iterations}")

    final_response = f"(El sub-agente '{name}' no generó respuesta)"

    # ── 4. LLM loop ─────────────────────────────────────────────────────────
    for iteration in range(1, max_iterations + 1):
        print(f"   ↻ Iteración {iteration}/{max_iterations}...", end="")

        try:
            call_start = time.time()
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=schemas if schemas else None,
                tool_choice="auto" if schemas else None,
            )
            call_duration_ms = (time.time() - call_start) * 1000

            # Log LLM call to tracer
            if tracer and trace:
                try:
                    tracer.log_llm_call(trace, name, messages, response, call_duration_ms)
                except Exception:
                    pass

            assistant_msg = response.choices[0].message

        except Exception as e:
            error_text = f"❌ Error en llamada LLM (iteración {iteration}): {e}"
            print(f" {error_text}")
            if state:
                try:
                    state.add_error(error_text)
                except Exception:
                    pass
            final_response = error_text
            break

        # ── No tool calls → final response ──────────────────────────────────
        if not assistant_msg.tool_calls:
            final_response = assistant_msg.content or final_response
            print(f" ✅ Respuesta final recibida.")
            # Append to messages for completeness
            messages.append({"role": "assistant", "content": final_response})
            break

        # ── Process tool calls ───────────────────────────────────────────────
        print(f" 🔧 {len(assistant_msg.tool_calls)} tool call(s)")

        # Append the assistant message (with tool_calls) to history
        messages.append({
            "role": "assistant",
            "content": assistant_msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant_msg.tool_calls
            ],
        })

        for tc in assistant_msg.tool_calls:
            result = execute_tool_call(
                tc, fn_map, config,
                tracer=tracer, trace=trace, state=state,
            )

            # Append tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })

            # Record for loop detection
            try:
                args_hash = hashlib.md5(tc.function.arguments.encode()).hexdigest()[:8]
                result_hash = hashlib.md5(str(result).encode()).hexdigest()[:8]
                loop_detector.record(tc.function.name, args_hash, result_hash)
            except Exception:
                pass

        # ── Loop detection ───────────────────────────────────────────────────
        loop_warning = loop_detector.check()
        if loop_warning:
            print(f"   {loop_warning}")
            messages.append({
                "role": "system",
                "content": loop_warning + " Cambiá tu estrategia o da tu respuesta final.",
            })

        # ── Context management ───────────────────────────────────────────────
        if context_manager.should_summarize(messages):
            print("   📝 Resumiendo historial de conversación...")
            try:
                messages = context_manager.summarize_history(messages)
            except Exception as e:
                print(f"   ⚠️ Error resumiendo: {e}")

        # ── Update state iteration count ─────────────────────────────────────
        if state:
            try:
                state.iteration_count += 1
            except Exception:
                pass

    else:
        # Max iterations reached without a final text response
        print(f"   ⚠️ Sub-agente '{name}' alcanzó el máximo de iteraciones ({max_iterations}).")
        final_response = (
            f"(El sub-agente '{name}' alcanzó el máximo de {max_iterations} "
            f"iteraciones sin respuesta final. Último contenido disponible.)"
        )
        # Try to get the last assistant content
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                final_response = msg["content"]
                break

    # ── 5. Update state with results ─────────────────────────────────────────
    if state:
        try:
            if name not in state.subagent_results:
                state.subagent_results[name] = []
            state.subagent_results[name].append(final_response)
        except Exception:
            pass

    print(f"   🏁 Sub-agente '{name}' finalizado.\n")
    return final_response


# ── Confirmation ─────────────────────────────────────────────────────────────────
print("🤖 Motor de sub-agentes inicializado.")
print(f"   Sub-agentes disponibles: {', '.join(SUBAGENT_TOOLS.keys())}")
for sa_name, tools in SUBAGENT_TOOLS.items():
    print(f"   • {sa_name}: {', '.join(tools)}")
