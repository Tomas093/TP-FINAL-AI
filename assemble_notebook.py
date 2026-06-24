#!/usr/bin/env python3
"""
Assembles individual cell .py files into a Colab notebook (.ipynb).
Reads from cells/ directory, creates Coding_agent.ipynb.
"""
import json
import os

CELLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cells")
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Coding_agent.ipynb")

def read_cell_file(filename):
    """Read a cell .py file and return its content."""
    path = os.path.join(CELLS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def make_cell(cell_type, source, collapsed=False):
    """Create a notebook cell dict."""
    # Split source into lines for notebook format
    lines = source.split('\n')
    source_list = []
    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            source_list.append(line + '\n')
        elif line:  # Last line only if non-empty
            source_list.append(line)
    
    cell = {
        "cell_type": cell_type,
        "source": source_list,
        "metadata": {}
    }
    if collapsed:
        cell["metadata"]["collapsed"] = True
    if cell_type == "code":
        cell["outputs"] = []
        cell["execution_count"] = None
    return cell

# ── Define notebook structure ──────────────────────────────────────────────────
# Each entry: (cell_type, source_or_filename, collapsed)
# For "code" cells: source_or_filename is a .py filename in cells/
# For "markdown" cells: source_or_filename is inline markdown text

NOTEBOOK_STRUCTURE = [
    ("markdown", """# 🤖 Coding Agent Avanzado — Kotlin / Spring Boot

**TP Final - Inteligencia Artificial**

Sistema multi-agente para análisis, corrección y mejora de proyectos Kotlin/Spring Boot.

### Arquitectura
- **Agente Principal (Orquestador)**: Recibe tareas, coordina subagentes, genera reportes
- **Explorer**: Analiza estructura del repositorio, arquitectura, dependencias
- **Researcher**: Busca en RAG (Kotlin/Spring Boot docs) y web
- **Implementer**: Propone y realiza cambios de código
- **Tester**: Ejecuta tests con Gradle, reporta resultados
- **Reviewer**: Revisa cambios y valida calidad

### Características
- 🔍 RAG sobre documentación Kotlin/Spring Boot (ChromaDB + OpenAI Embeddings)
- 💾 Memoria persistente por proyecto (JSON)
- 🔒 Políticas de seguridad configurables (YAML)
- 📊 Observabilidad con Langfuse
- 🔄 Detección de loops y gestión de contexto
- 🔌 Sistema de registro de herramientas (plugin-style)
"""),

    ("markdown", "### 📦 Instalación de dependencias"),
    ("code", "01_setup.py"),

    ("markdown", "### ⚙️ Configuración del cliente y políticas del agente"),
    ("code", "02_config.py"),

    ("markdown", "### 📊 Observabilidad con Langfuse"),
    ("code", "03_observability.py"),

    ("markdown", "### 📋 Estado compartido de tarea (TaskState)"),
    ("code", "04_state.py"),

    ("markdown", "### 💾 Memoria persistente del proyecto"),
    ("code", "05_memory.py"),

    ("markdown", """### 🔍 Motor RAG (Retrieval-Augmented Generation)

Sistema de búsqueda semántica sobre documentación técnica de Kotlin y Spring Boot.
- **Chunking**: Fragmentos de 500 caracteres con 50 de overlap
- **Embeddings**: OpenAI `text-embedding-3-small`
- **Vector Store**: ChromaDB (persistente en disco)
"""),
    ("code", "06_rag.py"),

    ("markdown", """### 🔧 Sistema de Herramientas (Tools)

Registro de herramientas con validación de políticas de seguridad.
Cada herramienta se registra con su esquema OpenAI, función de ejecución y tipo de permiso.
"""),
    ("code", "07_tools.py"),

    ("markdown", """### 🧠 Gestión de contexto y detección de loops

- **ContextManager**: Resume conversaciones largas para no exceder la ventana de contexto
- **LoopDetector**: Detecta acciones repetidas sin progreso y fuerza cambio de estrategia
"""),
    ("code", "08_context.py"),

    ("markdown", """### 🤖 Motor de Subagentes

5 subagentes especializados, cada uno con su propio prompt, herramientas permitidas y ciclo de ejecución.
"""),
    ("code", "09_subagents.py"),

    ("markdown", """### 🎯 Agente Principal (Orquestador)

Coordina el flujo de trabajo con **routing no lineal**:
- Explorer → Researcher → Implementer ↔ Tester (loop de reintentos) → Reviewer
- Detecta cuando un subagente está bloqueado y cambia de estrategia
- Genera reportes finales con atribución de fuentes
"""),
    ("code", "10_orchestrator.py"),

    ("markdown", """### 📚 Ingesta de documentación para RAG

Carga documentación de Kotlin, Spring Boot, Gradle y patrones comunes en el vector store.
"""),
    ("code", "11_ingestion.py"),

    ("markdown", """### 🏗️ Proyecto de demostración (Kotlin/Spring Boot)

Crea un proyecto Spring Boot con Kotlin que contiene bugs intencionales:
1. **Bug 1**: Uso inseguro de `!!` (non-null assertion) → `NullPointerException`
2. **Bug 2**: `ResponseEntity.ok()` en vez de `ResponseEntity.created()` (HTTP 201)
3. **Bug 3**: Sin validación de input (títulos vacíos permitidos)
"""),
    ("code", "12_demo.py"),

    ("markdown", """### ▶️ Ejecutar Agente

Ejecutar esta celda para iniciar el agente interactivo.

**Comandos disponibles:**
- `/plan on` / `/plan off` — Activar/desactivar modo plan
- `/supervision on` / `/supervision off` — Activar/desactivar modo supervisión
- `exit` — Salir

**Tareas de prueba sugeridas:**
1. `"Explorá este proyecto, ejecutá los tests, encontrá los bugs, corregílos y verificá la corrección"`
2. `"Agregá validación de input al TaskService para que no se permitan títulos vacíos, y escribí tests"`
3. `"Optimizá el proyecto"` (tarea ambigua → el agente debería pedir clarificación)
"""),
    ("code", "13_run.py"),
]

# ── Build notebook ─────────────────────────────────────────────────────────────
cells = []
for cell_type, source_or_file, *rest in NOTEBOOK_STRUCTURE:
    collapsed = rest[0] if rest else False
    
    if cell_type == "code":
        # Read from file
        source = read_cell_file(source_or_file)
    else:
        source = source_or_file
    
    cells.append(make_cell(cell_type, source, collapsed))

notebook = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {
        "colab": {
            "provenance": [],
            "toc_visible": True
        },
        "kernelspec": {
            "name": "python3",
            "display_name": "Python 3"
        },
        "language_info": {
            "name": "python"
        }
    },
    "cells": cells
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print(f"✅ Notebook generated: {OUTPUT}")
print(f"   Total cells: {len(cells)} ({sum(1 for c in cells if c['cell_type'] == 'code')} code, {sum(1 for c in cells if c['cell_type'] == 'markdown')} markdown)")
