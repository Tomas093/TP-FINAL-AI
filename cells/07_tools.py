# ── Cell 07: Tool Registry & Implementations ────────────────────────────────────
# Uses globals from prior cells: config, check_permission, TAVILY_API_KEY,
#                                 rag_search (cell 06), tracer, WORKSPACE

import os
import subprocess
import json
import time
import hashlib

from tavily import TavilyClient


def get_tools_for_agent(tool_names: list) -> tuple:
    """Return (schemas_list, fn_map) filtered to *tool_names*."""
    schemas: list = []
    fn_map: dict = {}
    for name in tool_names:
        entry = TOOL_REGISTRY.get(name)
        if entry:
            schemas.append(entry["schema"])
            fn_map[name] = entry["fn"]
    return schemas, fn_map


# ── Tool Implementations ────────────────────────────────────────────────────────

def tool_read_file(path: str) -> str:
    """Read and return the contents of a file."""
    try:
        allowed, reason = check_permission("read", path, config)
        if not allowed:
            return f"❌ Permiso denegado para leer '{path}': {reason}"
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        return f"❌ Error leyendo '{path}': {e}"


def tool_write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories if needed."""
    try:
        allowed, reason = check_permission("write", path, config)
        if not allowed:
            return f"❌ Permiso denegado para escribir '{path}': {reason}"
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Archivo escrito: {path} ({len(content)} caracteres)"
    except Exception as e:
        return f"❌ Error escribiendo '{path}': {e}"


def tool_list_files(directory: str) -> str:
    """List the contents of a directory."""
    try:
        allowed, reason = check_permission("read", directory, config)
        if not allowed:
            return f"❌ Permiso denegado para listar '{directory}': {reason}"
        if not os.path.isdir(directory):
            return f"❌ '{directory}' no es un directorio válido."
        entries = sorted(os.listdir(directory))
        result_lines: list = []
        for entry in entries:
            full = os.path.join(directory, entry)
            kind = "📁" if os.path.isdir(full) else "📄"
            result_lines.append(f"  {kind} {entry}")
        return f"Contenido de '{directory}' ({len(entries)} elementos):\n" + "\n".join(result_lines)
    except Exception as e:
        return f"❌ Error listando '{directory}': {e}"


def tool_run_command(command: str) -> str:
    """Run a shell command in the workspace directory and return stdout+stderr."""
    try:
        allowed, reason = check_permission("command", command, config)
        if not allowed:
            return f"❌ Permiso denegado para ejecutar '{command}': {reason}"

        # Run from workspace directory
        workspace_dir = config.get("workspace", WORKSPACE) if config else "."
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=workspace_dir or ".",
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n--- STDERR ---\n" + result.stderr) if output else result.stderr
        if not output.strip():
            output = "(sin salida)"
        return f"[exit code: {result.returncode}]\n{output}"

    except subprocess.TimeoutExpired:
        return f"❌ Timeout: el comando excedió 120 segundos: '{command}'"
    except Exception as e:
        return f"❌ Error ejecutando comando: {e}"


def tool_web_search(query: str) -> str:
    """Search the web via Tavily and return formatted results."""
    try:
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        response = tavily.search(query=query, max_results=5)
        results = response.get("results", [])
        if not results:
            return "No se encontraron resultados web."
        formatted: list = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "Sin título")
            url = r.get("url", "")
            snippet = r.get("content", "")[:300]
            formatted.append(f"{i}. **{title}**\n   URL: {url}\n   {snippet}")
        return "\n\n".join(formatted)
    except Exception as e:
        return f"❌ Error en búsqueda web: {e}"


def tool_rag_search(query: str, n_results: int = 5) -> str:
    """Search the RAG knowledge base."""
    try:
        return rag_search(query, n_results=n_results)
    except Exception as e:
        return f"❌ Error en búsqueda RAG: {e}"


# ── execute_tool_call ────────────────────────────────────────────────────────────

def execute_tool_call(tool_call, allowed_fns: dict, config: dict,
                      tracer=None, trace=None, state=None) -> str:
    """Execute a single tool call with policy check, logging, and state updates."""
    tool_name = tool_call.function.name
    start_time = time.time()

    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as e:
        return f"❌ Error parseando argumentos de '{tool_name}': {e}"

    # Check if tool is allowed for this agent
    if tool_name not in allowed_fns:
        return f"❌ Herramienta '{tool_name}' no permitida para este sub-agente."

    # Check permission via registry
    registry_entry = TOOL_REGISTRY.get(tool_name, {})
    perm_type = registry_entry.get("permission_type")
    if perm_type:
        # Determine target for permission check
        target = args.get("path") or args.get("directory") or args.get("command") or args.get("query", "")
        allowed, reason = check_permission(perm_type, target, config)
        if not allowed:
            return f"❌ Permiso denegado para '{tool_name}' sobre '{target}': {reason}"

    # Execute
    fn = allowed_fns[tool_name]
    
    # Supervisión Global (Human-in-the-loop)
    if config.get("supervision_mode") and tool_name in ["write_file", "run_command"]:
        action_desc = f"escribir en '{args.get('path')}'" if tool_name == "write_file" else f"ejecutar el comando '{args.get('command')}'"
        user_input = input(f"🔒 [Supervisión] El agente intenta {action_desc}.\n¿Aprobar acción? (s/n): ")
        if user_input.strip().lower() not in ("s", "si", "sí", "y", "yes"):
            return f"🚫 Acción rechazada por el usuario en modo supervisión."
    
    try:
        result = fn(**args)
    except TypeError as e:
        result = f"❌ Error en argumentos de '{tool_name}': {e}"
    except Exception as e:
        result = f"❌ Error ejecutando '{tool_name}': {e}"

    duration_ms = (time.time() - start_time) * 1000

    # Log to tracer
    if tracer and trace:
        try:
            tracer.log_tool_call(trace, tool_name, args, str(result)[:500], duration_ms)
            if tool_name == "rag_search":
                tracer.log_rag_retrieval(trace, args.get("query", ""), [{"content": str(result)[:1500]}])
        except Exception:
            pass  # Don't let tracing break the flow

    # Update state
    if state:
        try:
            args_str = json.dumps(args, ensure_ascii=False)
            state.record_action(tool_name, args_str, str(result)[:200])

            # Track sources for rag and web searches
            if tool_name == "rag_search":
                state.add_source("rag", args.get("query", ""), str(result)[:100])
            elif tool_name == "web_search":
                state.add_source("web", args.get("query", ""), str(result)[:100])
            elif tool_name == "write_file":
                state.mark_file_modified(args.get("path", ""))
        except Exception:
            pass

    return str(result)


# ── Static Tool Registry ───────────────────────────────────────────────────────────

TOOL_REGISTRY: dict = {
    "read_file": {
        "schema": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Lee el contenido de un archivo dado su path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta absoluta al archivo a leer."},
                    },
                    "required": ["path"],
                },
            },
        },
        "fn": tool_read_file,
        "permission_type": "read",
    },
    "write_file": {
        "schema": {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Escribe contenido en un archivo. Crea directorios intermedios si no existen.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta absoluta al archivo a escribir."},
                        "content": {"type": "string", "description": "Contenido a escribir en el archivo."},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        "fn": tool_write_file,
        "permission_type": "write",
    },
    "list_files": {
        "schema": {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "Lista el contenido de un directorio.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Ruta absoluta al directorio a listar."},
                    },
                    "required": ["directory"],
                },
            },
        },
        "fn": tool_list_files,
        "permission_type": "read",
    },
    "run_command": {
        "schema": {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Ejecuta un comando de shell en el directorio del workspace y devuelve stdout+stderr.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Comando de shell a ejecutar."},
                    },
                    "required": ["command"],
                },
            },
        },
        "fn": tool_run_command,
        "permission_type": "command",
    },
    "web_search": {
        "schema": {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Busca información en la web usando Tavily. Devuelve hasta 5 resultados.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Consulta de búsqueda web."},
                    },
                    "required": ["query"],
                },
            },
        },
        "fn": tool_web_search,
        "permission_type": None,
    },
    "rag_search": {
        "schema": {
            "type": "function",
            "function": {
                "name": "rag_search",
                "description": "Busca en la base de conocimiento RAG (documentación Kotlin/Spring Boot indexada).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Consulta de búsqueda en la base RAG."},
                        "n_results": {"type": "integer", "description": "Número de resultados (default 5)."},
                    },
                    "required": ["query"],
                },
            },
        },
        "fn": tool_rag_search,
        "permission_type": None,
    },
}

# ── Confirmation ─────────────────────────────────────────────────────────────────
print("🛠️  Tool Registry inicializado.")
print(f"   Herramientas registradas ({len(TOOL_REGISTRY)}):")
for name, entry in TOOL_REGISTRY.items():
    perm = entry["permission_type"] or "sin restricción"
    print(f"   • {name} — permiso: {perm}")
