# Coding Agent Avanzado - Kotlin/Spring Boot

## Descripción del caso de uso
Este proyecto implementa un sistema multi-agente diseñado para analizar y corregir bugs en un proyecto basado en Spring Boot y Kotlin.
El entorno incluye herramientas locales, RAG (Retrieval-Augmented Generation) sobre documentación técnica de Kotlin y Spring, memoria persistente, y capacidades de testing automatizado usando Gradle.

## Arquitectura
El sistema no utiliza frameworks de orquestación externos (como LangChain o AutoGen). Todo está implementado de forma nativa en un entorno de notebook.
Consiste de un **Orquestador (Agente Principal)** y 5 subagentes especializados:

1. **Explorer**: Explora el repositorio, analiza dependencias y estructura general.
2. **Researcher**: Busca información en la base de datos documental (RAG) o en la web.
3. **Implementer**: Escribe o modifica código (Kotlin/Spring) de forma idiomática.
4. **Tester**: Ejecuta pruebas automáticas (via Gradle) y reporta resultados.
5. **Reviewer**: Revisa los cambios realizados en el código verificando calidad y convenciones.

## Instrucciones de Instalación
1. Abrí el notebook (`Coding_agent.ipynb`) en Google Colab.
2. En la barra lateral izquierda, abrí la pestaña de "Secrets" (llave).
3. Configurá las siguientes API keys:
   - `OPENAI_API_KEY`: Tu clave de OpenAI.
   - `TAVILY_API_KEY`: Tu clave de Tavily (para búsquedas web).
   - `LANGFUSE_PUBLIC_KEY`: Tu clave pública de Langfuse (opcional para observabilidad).
   - `LANGFUSE_SECRET_KEY`: Tu clave secreta de Langfuse (opcional para observabilidad).

## Instrucciones de Ejecución
1. Ejecutá todas las celdas en orden.
2. La última celda iniciará la interfaz de consola interactiva.
3. Podés interactuar con el agente en español e indicarle tareas como: `"Encontrá los bugs en el proyecto, corregílos y validá con los tests"`.
4. El agente cuenta con enrutamiento no lineal: Si el implementador hace cambios pero los tests fallan, la tarea volverá automáticamente al implementador (hasta 3 intentos) para corregir el código en base a los errores del tester.

## Documentación de la Base RAG
- **Fuentes**: Documentación oficial de Kotlin, Spring Boot, Spring Data JPA, Testing en Spring y Gradle Kotlin DSL.
- **Estrategia de Chunking**: Tramos de 500 caracteres con 50 de superposición.
- **Embeddings**: `text-embedding-3-small` de OpenAI.
- **Almacenamiento**: Base vectorial ChromaDB con distancia Coseno, persistida en disco.

## Estado Compartido (TaskState)
Todos los agentes comparten un objeto `TaskState` que registra:
- La petición original.
- Archivos modificados y fuentes consultadas.
- Historial de acciones (para detección de loops infinitos).
- Observaciones y errores.
- Una función `to_summary()` se encarga de truncar el estado agresivamente (<1500 caracteres) para mantener limpia la ventana de contexto.

## Memoria Persistente (ProjectMemory)
El sistema recuerda el estado global del proyecto entre distintas tareas y ejecuciones guardando la arquitectura descubierta, archivos importantes y comandos útiles en un archivo JSON local.

## Políticas de Seguridad
Las herramientas del agente están limitadas por el archivo `agent.config.yaml`, definiendo patrones (globs) de denegación tanto para lectura como escritura (p. ej. protección de claves secretas). Ciertos comandos de terminal como git commit o gradle run requieren explícita autorización interactiva del usuario.

## Observabilidad
Se integró **Langfuse** para monitorear el consumo de tokens, costo estimado por llamada al LLM, la ejecución de las herramientas, el uso de RAG y el árbol de trazas para cada tarea enviada al sistema multi-agente.
# TP-FINAL-AI
