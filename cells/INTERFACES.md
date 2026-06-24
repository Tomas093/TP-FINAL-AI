# Shared Interface Contract — Coding Agent Avanzado

All cells run sequentially in one Colab notebook. Later cells reference globals from earlier cells.
Each cell file (01_setup.py through 13_run.py) contains ONLY the Python code for that cell.
Markdown cells are handled separately by the assembler.

## Cell Order & Dependencies

```
01_setup.py        → pip installs, sqlite3 fix, JDK/Gradle install. No deps.
02_config.py       → OpenAI client, config loader, policy checker. No deps.
03_observability.py → Langfuse Tracer class. Uses: userdata.
04_state.py        → TaskState class. No deps.
05_memory.py       → ProjectMemory class. No deps.
06_rag.py          → ChromaDB RAG engine. Uses: client, EMBEDDING_MODEL.
07_tools.py        → Tool registry + 6 tools. Uses: config, check_permission, rag_search, TavilyClient.
08_context.py      → ContextManager + LoopDetector. Uses: client, MODEL.
09_subagents.py    → 5 system prompts + run_subagent(). Uses: TaskState, get_tools_for_agent, execute_tool_call, ContextManager, LoopDetector, Tracer.
10_orchestrator.py → Main agent loop with non-linear routing. Uses: everything above + ProjectMemory.
11_ingestion.py    → Ingests Kotlin/Spring Boot docs into RAG. Uses: ingest_document, rag_collection.
12_demo.py         → Creates demo Kotlin/Spring Boot project with bugs. No deps.
13_run.py          → Calls run_agent(). Uses: run_agent.
```

## Globals (defined in 02_config.py, available to all subsequent cells)

```python
from google.colab import userdata
from openai import OpenAI

client = OpenAI(api_key=userdata.get("OPENAI_API_KEY"))
MODEL = "gpt-5-nano"
EMBEDDING_MODEL = "text-embedding-3-small"
TAVILY_API_KEY = userdata.get("TAVILY_API_KEY")
config = {}  # Populated after load_config() is called
WORKSPACE = ""  # Set after config is loaded
```

## Interface: load_config / check_permission (02_config.py)

```python
def load_config(path: str = "agent.config.yaml") -> dict:
    """Load and return the YAML config. Also sets global `config` and `WORKSPACE`."""

def check_permission(action_type: str, target: str, config: dict) -> tuple:
    """
    Check if an action is allowed by the security policies.
    action_type: "read" | "write" | "command"
    target: file path or command string
    Returns: (allowed: bool, reason: str)
    Uses fnmatch glob matching against config["permissions"][action_type]["deny"]
    For commands, also checks "require_approval" list.
    """
```

## Interface: Tracer (03_observability.py)

```python
class Tracer:
    def __init__(self):
        """Initialize Langfuse client using userdata keys."""
        # Uses: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST

    def start_trace(self, name: str, user_id: str = "user"):
        """Start a new Langfuse trace. Returns the trace object."""

    def log_llm_call(self, trace, agent_name: str, messages: list, response, duration_ms: float):
        """Log an LLM generation with model, tokens, cost, latency."""

    def log_tool_call(self, trace, tool_name: str, args: dict, result: str, duration_ms: float):
        """Log a tool execution as a span."""

    def log_rag_retrieval(self, trace, query: str, results: list):
        """Log a RAG retrieval as a span."""

    def flush(self):
        """Flush pending events to Langfuse."""

# Global instance:
tracer = Tracer()
```

## Interface: TaskState (04_state.py)

```python
class TaskState:
    def __init__(self, original_request: str):
        self.original_request = original_request
        self.status = "planning"  # planning|exploring|researching|implementing|testing|reviewing|done|blocked
        self.plan = []
        self.current_step = 0
        self.subagent_results = {}   # {agent_name: [result_strings]}
        self.sources_consulted = []  # [{"type": "rag"|"web"|"repo"|"memory", "ref": str, "snippet": str}]
        self.files_modified = []
        self.observations = []
        self.errors = []
        self.iteration_count = 0
        self.action_history = []     # [{"action": str, "args_hash": str, "result_hash": str}]

    def add_source(self, source_type: str, ref: str, snippet: str): ...
    def add_observation(self, text: str): ...
    def mark_file_modified(self, path: str): ...
    def add_error(self, error: str): ...
    def record_action(self, action: str, args: str, result: str): ...
    def to_summary(self) -> str:
        """COMPACT summary for LLM context. Truncates old errors/observations to last 5.
        Limits source snippets to 100 chars each. Total output < 1500 chars."""
    def to_dict(self) -> dict: ...
```

## Interface: ProjectMemory (05_memory.py)

```python
class ProjectMemory:
    def __init__(self, project_name: str, base_dir: str = "./data/memory"):
        self.project_name = project_name
        self.base_dir = base_dir
        self.data = {
            "architecture": "",
            "important_files": {},
            "dependencies": [],
            "commands": {},
            "conventions": [],
            "decisions": [],
            "bugs": [],
            "session_summaries": []
        }

    def load(self): """Load from JSON file if it exists."""
    def save(self): """Save to JSON file, creating dirs as needed."""
    def update(self, section: str, data): """Update a section of memory."""
    def get_context_summary(self) -> str:
        """Compact string (< 800 chars) for injecting into system prompts.
        Summarizes architecture, key files, commands, recent decisions."""
```

## Interface: RAG Engine (06_rag.py)

```python
import chromadb

rag_collection = None  # Set by init_rag()

def init_rag(persist_dir: str = "./data/chroma"):
    """Initialize ChromaDB client and collection. Sets global rag_collection."""

def chunk_document(text: str, source_name: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """Split text into overlapping chunks. Returns list of {"text": str, "metadata": {"source": str, "chunk_index": int}}."""

def embed_and_store(chunks: list, collection):
    """Generate embeddings with OpenAI and store in ChromaDB."""

def rag_search(query: str, n_results: int = 5) -> str:
    """Search RAG. Returns formatted string with ranked results including source attribution."""

def ingest_document(text: str, source_name: str, collection=None):
    """Convenience: chunk + embed + store. Uses global rag_collection if collection is None."""
```

## Interface: Tool Registry (07_tools.py)

```python
TOOL_REGISTRY = {}  # name -> {"schema": dict, "fn": callable, "permission_type": str|None}

def register_tool(name: str, description: str, params_schema: dict, fn, permission_type: str = None):
    """Register a tool with its OpenAI function schema and execution function."""

def get_tools_for_agent(tool_names: list) -> tuple:
    """Returns (openai_tool_schemas: list[dict], fn_map: dict[str, callable]) filtered to given names."""

def execute_tool_call(tool_call, allowed_fns: dict, config: dict, tracer=None, trace=None, state=None) -> str:
    """Execute a tool call with: policy check → permission check → execution → logging.
    Updates state.record_action() and state.add_source() if state is provided.
    Returns the tool result as a string."""

# Registered tools: read_file, write_file, list_files, run_command, web_search, rag_search
# Each tool function has signature matching its OpenAI schema parameters.
```

## Interface: Context & Loop Detection (08_context.py)

```python
class ContextManager:
    def __init__(self, max_tokens: int = 20000):
        self.max_tokens = max_tokens

    def estimate_tokens(self, messages: list) -> int:
        """Rough estimate: 1 token ≈ 4 chars."""

    def should_summarize(self, messages: list) -> bool:
        """True if estimated tokens > 70% of max_tokens."""

    def summarize_history(self, messages: list) -> list:
        """Call LLM to summarize older messages. Keep system prompt + last 6 messages.
        Returns new messages list with summary injected."""

class LoopDetector:
    def __init__(self, max_repeats: int = 3):
        self.history = []
        self.max_repeats = max_repeats

    def record(self, action: str, args_hash: str, result_hash: str):
        """Record an action for loop detection."""

    def check(self) -> str:
        """Returns warning message if loop detected (same action+args+result repeated >= max_repeats).
        Returns None if no loop."""

    def reset(self):
        """Clear history."""
```

## Interface: Subagent Engine (09_subagents.py)

```python
# System prompts for each subagent (specialized for Kotlin/Spring Boot)
EXPLORER_PROMPT = "..."   # Maps repo: build.gradle.kts, packages, Spring annotations, entry points
RESEARCHER_PROMPT = "..."  # RAG first, web fallback, cites sources
IMPLEMENTER_PROMPT = "..." # Writes idiomatic Kotlin, Spring conventions, minimal changes
TESTER_PROMPT = "..."      # Runs gradle test, parses output, reports don't fix
REVIEWER_PROMPT = "..."    # Reviews changes, checks Kotlin idioms, null safety, edge cases

SUBAGENT_TOOLS = {
    "explorer":    ["list_files", "read_file", "run_command"],
    "researcher":  ["rag_search", "web_search", "read_file"],
    "implementer": ["read_file", "write_file", "list_files"],
    "tester":      ["run_command", "read_file"],
    "reviewer":    ["run_command", "read_file"]
}

def run_subagent(name: str, task: str, state: TaskState, config: dict,
                 tracer=None, trace=None, memory: ProjectMemory = None) -> str:
    """
    Runs a subagent with its own message history and filtered tools.
    1. Build system prompt (includes state summary + memory context if available)
    2. Run LLM loop with allowed tools only
    3. Use LoopDetector to detect repetition
    4. Use ContextManager to manage conversation length
    5. Update state.subagent_results[name] with result
    6. Log all LLM/tool calls to Langfuse via tracer
    7. Max iterations from config["max_iterations"] (default 15 per subagent)
    Returns the subagent's final text response.
    """
```

## Interface: Orchestrator (10_orchestrator.py)

```python
def run_agent():
    """
    Main interactive loop. Handles:
    1. User input (chat, /plan on|off, /supervision on|off, exit)
    2. Creates TaskState per task
    3. Loads ProjectMemory
    4. Creates Langfuse trace
    5. Dispatches subagents with NON-LINEAR routing:
       - Explorer → Researcher → Implementer → Tester
       - If Tester fails: loop back to Implementer (max 3 retries)
       - After success (or max retries): Reviewer
    6. Generates final report with source attribution
    7. Saves memory
    8. Flushes Langfuse
    
    For the Reviewer: saves original file contents BEFORE Implementer runs,
    so Reviewer can compare before/after without needing git diff.
    """
```

## Interface: RAG Ingestion (11_ingestion.py)

```python
# This cell calls ingest_document() for each doc:
# - Kotlin null safety, data classes, when expressions, extension functions
# - Spring Boot: @RestController, @Service, @Repository, @Entity, DI, auto-config
# - Spring Data JPA: repositories, query methods
# - Testing: JUnit 5, @SpringBootTest, MockMvc
# - Gradle Kotlin DSL basics
# - Common error patterns
# Each document is a multiline string with clear section headings.
```

## Interface: Demo Project (12_demo.py)

```python
# Installs JDK + Gradle if needed
# Creates workspace/demo-spring-app/ with:
#   build.gradle.kts (Spring Boot + Kotlin plugin)
#   settings.gradle.kts
#   src/main/kotlin/com/demo/DemoApplication.kt
#   src/main/kotlin/com/demo/model/Task.kt (data class)
#   src/main/kotlin/com/demo/repository/TaskRepository.kt (in-memory, no DB)
#   src/main/kotlin/com/demo/service/TaskService.kt (has null safety bug)
#   src/main/kotlin/com/demo/controller/TaskController.kt (has wrong HTTP status bug)
#   src/test/kotlin/com/demo/service/TaskServiceTest.kt (tests that expose bugs)

# Intentional bugs:
# 1. TaskService.findById() does `repository.findById(id)!!` instead of safe handling → NPE
# 2. TaskController.createTask() returns ResponseEntity.ok() instead of .created()
# 3. No input validation on Task title (empty strings allowed)
```

## Coding Guidelines

- Language: Python 3.10+ (Colab default)
- Comments: English
- Print statements / user-facing: Spanish
- Each cell file is PURE Python code (no markdown, no !pip, no cell magic) EXCEPT 01_setup.py which uses !pip and !apt-get
- Use `import` statements at the top of each cell file if needed (Colab allows re-importing)
- Use `global` keyword when modifying module-level variables inside functions
- Error handling: use try/except, never let a cell crash the notebook
- All string formatting: f-strings
- Type hints where practical
