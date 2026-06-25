# TP-FINAL-AI: Coding Agent Avanzado - Kotlin/Spring Boot

## 1. Instrucciones de Instalación, Configuración y Ejecución

### Instalación y Configuración
1. Abrí el notebook https://colab.research.google.com/drive/1q008OEbI1a8EtJV_ePHiPeUIHpk1daf4?usp=sharing en Google Colab.
2. Configurá las siguientes API keys:
   - `OPENAI_API_KEY`: Tu clave de OpenAI.
   - `TAVILY_API_KEY`: Tu clave de Tavily (para búsquedas web).
   - `LANGFUSE_PUBLIC_KEY`: Tu clave pública de Langfuse (opcional para observabilidad).
   - `LANGFUSE_SECRET_KEY`: Tu clave secreta de Langfuse (opcional para observabilidad).

### Ejecución
1. Ejecutá todas las celdas en orden.
2. La última celda iniciará la interfaz de consola interactiva.
3. Podés interactuar con el agente en español e indicarle tareas como: `"Encontrá los bugs en el proyecto, corregílos y validá con los tests"`.

## 2. Breve descripción del caso de uso elegido

- **Repositorio o proyecto utilizado**: Proyecto base en Spring Boot y Kotlin diseñado para análisis automatizado de código, conteniendo bugs intencionales o tareas nuevas por implementar.
- **Objetivo concreto**: Construir un sistema multi-agente autónomo capaz de analizar un proyecto, diagnosticar y encontrar bugs, implementar las correcciones o código necesario de forma idiomática (Spring/Kotlin) y probar esos cambios automáticamente.
- **Criterio para considerar que fue cumplido**: El agente debe ser capaz de explorar el repositorio exitosamente sin intervención humana, identificar correctamente el origen de los fallos (o los requerimientos para nuevas features), aplicar parches al código fuente y validar iterativamente mediante la ejecución del test suite del proyecto (vía Gradle) que el comportamiento ahora es el esperado.

## 3. Explicación Detallada de la Arquitectura

El sistema implementa un patrón **Supervisor-Worker (Orquestador-Subagentes)** basado en un modelo de **Máquina de Estados (State Graph)** dirigida por un LLM. Todo el sistema funciona en un ciclo continuo (*Agentic Loop*) donde el control y el estado mutan a medida que diferentes nodos toman acción. No se utilizan frameworks de caja negra; el ruteo y el flujo de ejecución son completamente explícitos.

### Rol del Agente Principal (Orquestador)
El **Orquestador** funciona como un "Router Node" lógico. Su única responsabilidad es evaluar el estado actual y determinar a qué subagente delegar la siguiente tarea en base a un flujo estrictamente controlado (ej: iniciar exploración, mandar a testear el código implementado, reenviar errores al implementador). No ejecuta herramientas de código directamente, sino que gestiona la memoria global y dirige el ciclo de corrección autónoma.

### Rol de cada Subagente
1. **Explorer**: Encargado de la fase de descubrimiento. Explora el repositorio local, analiza el árbol de dependencias, lee directorios y escanea archivos para conformar un entendimiento rápido del proyecto base.
2. **Researcher**: Busca información técnica y de referencia en la base documental interna del proyecto (RAG) o en la web (vía Tavily) para resolver dudas de sintaxis o convenciones.
3. **Implementer**: Recibe instrucciones concretas y altera el código fuente. Utiliza herramientas de edición para crear, reemplazar o borrar líneas de código de forma idiomática.
4. **Tester**: Ejecuta los procesos de validación automática localmente (por ejemplo, compilación o pruebas vía `./gradlew test`). Inyecta los logs de error (si los hay) en el estado para que el Orquestador ordene una corrección iterativa (`Implementer -> Tester -> Implementer`).
5. **Reviewer**: Revisa los cambios antes de que sean considerados finalizados, garantizando la calidad del código, la cobertura lógica y la adherencia a las convenciones del equipo.

### Estructura del Estado Compartido (TaskState)
En lugar de pasar un historial de chat infinito, la comunicación entre agentes se logra pasándose un único objeto de estado centralizado (`TaskState`) que se va enriqueciendo. Contiene:
- **Petición Original y Contexto Global**: Para mantener al modelo enfocado en el objetivo real.
- **Historial de Trazas (Execution Path)**: Un arreglo secuencial (ej. `[Orchestrator -> Explorer -> Orchestrator -> Implementer -> Tester]`) que resulta esencial para que el sistema detecte si se ha atascado en un loop infinito.
- **Observaciones y Errores**: Bitácora acumulativa de dependencias faltantes, código roto o fallos de compilación detectados por el Tester.
- **Compresión Activa**: Para evitar que el consumo de tokens explote, el estado ejecuta el método `to_summary()` antes de cada llamada al LLM. Esta función trunca agresivamente las respuestas kilométricas de consola y sintetiza eventos antiguos, garantizando que el contexto se mantenga limpio y por debajo de los 1500 caracteres, permitiendo tareas de larga duración.

---

## 4. Otros detalles del sistema

### Documentación de la Base RAG
- **Fuentes**: Documentación oficial de Kotlin, Spring Boot, Spring Data JPA, Testing en Spring y Gradle Kotlin DSL, junto con convenciones específicas del proyecto.
- **Estrategia de Chunking**: Tramos de 500 caracteres con 50 de superposición.
- **Embeddings**: `text-embedding-3-small` de OpenAI.
- **Almacenamiento**: Base vectorial ChromaDB con distancia Coseno, persistida en disco local.

### Memoria Persistente (ProjectMemory)
El sistema recuerda el estado global del proyecto entre distintas tareas y sesiones de ejecución, persistiendo en un archivo JSON información como la estructura del proyecto, archivos clave y comandos útiles descubiertos.

### Políticas de Seguridad
Las herramientas que editan código o leen el sistema de archivos están restringidas por un `agent.config.yaml`, donde se configuran globs de denegación para proteger directorios sensibles o credenciales en el entorno.

### Observabilidad
El orquestador incluye trazabilidad completa usando **Langfuse**. Cada solicitud de usuario genera un árbol de trazas donde se registra el razonamiento, el costo, la latencia de las herramientas utilizadas y el número de tokens procesados por la IA en cada paso.
