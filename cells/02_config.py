# =============================================================================
# Cell 02 — Configuration: OpenAI Client, YAML Config, Permission Checker
# =============================================================================
# Sets up the OpenAI client, defines the agent config YAML (workspace, model,
# ecosystem, permissions with deny/require_approval lists), and provides
# load_config() and check_permission() functions.
# =============================================================================

import os
import yaml
import fnmatch
from openai import OpenAI
from google.colab import userdata

# --- OpenAI Client ---
client: OpenAI = OpenAI(api_key=userdata.get("OPENAI_API_KEY"))

# --- Model Configuration ---
MODEL: str = "gpt-5-nano"
EMBEDDING_MODEL: str = "text-embedding-3-small"

# --- Tavily API Key (for web search) ---
TAVILY_API_KEY: str = userdata.get("TAVILY_API_KEY")

# --- Global config and workspace (populated by load_config()) ---
config: dict = {}
WORKSPACE: str = ""

# --- Write the agent configuration YAML to disk ---
_CONFIG_YAML_CONTENT: str = """\
# Agent Configuration — Kotlin/Spring Boot Coding Agent
workspace: "./workspace/demo-spring-app"

model:
  name: "gpt-5-nano"
  temperature: 0.2
  max_tokens: 4096

ecosystem:
  language: "kotlin"
  framework: "spring-boot"
  build_tool: "gradle"
  test_framework: "junit5"

permissions:
  read:
    deny:
      - "/etc/shadow"
      - "/etc/passwd"
      - "**/.env"
      - "**/secrets/**"
      - "**/*.pem"
      - "**/*.key"
  write:
    deny:
      - "/etc/**"
      - "/usr/**"
      - "/bin/**"
      - "/sbin/**"
      - "**/.git/**"
      - "**/node_modules/**"
  command:
    deny:
      - "rm -rf /"
      - "rm -rf /*"
      - "sudo *"
      - "curl * | bash"
      - "wget * | bash"
      - "chmod 777 *"
      - "shutdown*"
      - "reboot*"
    require_approval:
      - "rm *"
      - "mv *"
      - "gradle clean*"
      - "kill *"

max_iterations: 25
"""

_CONFIG_PATH: str = "agent.config.yaml"
if not os.path.exists(_CONFIG_PATH):
    with open(_CONFIG_PATH, "w") as f:
        f.write(_CONFIG_YAML_CONTENT)


def load_config(path: str = "agent.config.yaml") -> dict:
    """
    Load the YAML config file and set global `config` and `WORKSPACE`.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        The parsed configuration dictionary.
    """
    global config, WORKSPACE
    try:
        with open(path, "r") as f:
            config = yaml.safe_load(f)

        # Set the workspace directory (create if needed)
        WORKSPACE = config.get("workspace", "./workspace")
        os.makedirs(WORKSPACE, exist_ok=True)

        return config
    except Exception as e:
        print(f"❌ Error al cargar configuración: {e}")
        config = {}
        WORKSPACE = "./workspace"
        os.makedirs(WORKSPACE, exist_ok=True)
        return config


def check_permission(action_type: str, target: str, config: dict) -> tuple:
    """
    Check if an action is allowed by the security policies.

    Uses fnmatch glob matching against the deny lists in config["permissions"].
    For commands, also checks the require_approval list and prompts the user
    for confirmation via input() if needed.

    Args:
        action_type: One of "read", "write", or "command".
        target: The file path or command string to check.
        config: The loaded configuration dictionary.

    Returns:
        A tuple of (allowed: bool, reason: str).
    """
    try:
        permissions = config.get("permissions", {})
        action_perms = permissions.get(action_type, {})
        deny_list = action_perms.get("deny", [])

        # Check against deny list using glob matching
        for pattern in deny_list:
            if fnmatch.fnmatch(target, pattern):
                return (False, f"Acción denegada: '{target}' coincide con patrón bloqueado '{pattern}'")

        # For commands, also check the require_approval list
        if action_type == "command" and not config.get("supervision_mode"):
            approval_list = action_perms.get("require_approval", [])
            for pattern in approval_list:
                if fnmatch.fnmatch(target, pattern):
                    print(f"\n⚠️  El comando requiere aprobación: {target}")
                    print(f"   (coincide con patrón: '{pattern}')")
                    user_input = input("   ¿Aprobar ejecución? (s/n): ").strip().lower()
                    if user_input not in ("s", "si", "sí", "y", "yes"):
                        return (False, f"Comando rechazado por el usuario: '{target}'")
                    break  # Approved, no need to check further patterns

        return (True, "Permitido")

    except Exception as e:
        # Fail-safe: deny if we can't check permissions
        return (False, f"Error al verificar permisos: {e}")


# --- Initialize config on cell execution ---
load_config()

# --- Print summary ---
print("=" * 60)
print("✅ Cliente OpenAI configurado")
print(f"   Modelo: {MODEL}")
print(f"   Embedding: {EMBEDDING_MODEL}")
print(f"✅ TAVILY_API_KEY configurada")
print(f"✅ Configuración cargada desde: {_CONFIG_PATH}")
print(f"   Workspace: {WORKSPACE}")
print(f"   Ecosistema: {config.get('ecosystem', {}).get('language', '?')}"
      f"/{config.get('ecosystem', {}).get('framework', '?')}")
print(f"   Max iteraciones: {config.get('max_iterations', '?')}")
print(f"   Patrones denegados (read): {len(config.get('permissions', {}).get('read', {}).get('deny', []))}")
print(f"   Patrones denegados (write): {len(config.get('permissions', {}).get('write', {}).get('deny', []))}")
print(f"   Patrones denegados (command): {len(config.get('permissions', {}).get('command', {}).get('deny', []))}")
print(f"   Requieren aprobación: {len(config.get('permissions', {}).get('command', {}).get('require_approval', []))}")
print("=" * 60)
