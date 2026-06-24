import sys
import os
import traceback
import json

def run_agent():
    """
    Main interactive loop. Handles:
    1. User input (chat, /plan on|off, /supervision on|off, exit)
    2. Creates TaskState per task
    3. Loads ProjectMemory
    4. Creates Langfuse trace
    5. Dispatches subagents with NON-LINEAR routing
    """
    plan_mode = False
    supervision_mode = False

    print("=================================================================")
    print("🤖 Coding Agent Avanzado (Kotlin/Spring Boot) iniciado.")
    print("   Comandos especiales: /plan on|off · /supervision on|off · exit")
    print("=================================================================\n")

    # Outer loop: read user input
    while True:
        try:
            user_input = input("\n👤 Usuario: ").strip()
        except EOFError:
            break

        if not user_input:
            continue

        lower_input = user_input.lower()
        if lower_input in ("exit", "quit"):
            print("👋 Terminando ejecución...")
            break

        if lower_input == "/plan on":
            plan_mode = True
            print("📋 Modo Plan ACTIVADO.")
            continue
        elif lower_input == "/plan off":
            plan_mode = False
            print("📋 Modo Plan DESACTIVADO.")
            continue
        elif lower_input == "/supervision on":
            supervision_mode = True
            print("🔒 Modo Supervisión ACTIVADO.")
            continue
        elif lower_input == "/supervision off":
            supervision_mode = False
            print("🔒 Modo Supervisión DESACTIVADO.")
            continue

        # Normal input processing
        print("\n⚙️ Iniciando nueva tarea...")
        
        # 2. Create TaskState
        state = TaskState(original_request=user_input)
        
        # 3. Load ProjectMemory
        project_name = os.path.basename(WORKSPACE.rstrip('/')) if WORKSPACE else "default_project"
        memory = ProjectMemory(project_name=project_name)
        memory.load()

        # 4. Start Langfuse trace
        trace = tracer.start_trace(name=f"Task: {user_input[:50]}...", user_id="user")

        try:
            # PLAN PHASE
            if plan_mode:
                print("📝 Generando plan de ejecución...")
                plan_messages = [
                    {"role": "system", "content": "You are a planning agent. Given a user request, output a step-by-step numbered plan to accomplish it. Do NOT output any tool calls, just text."},
                    {"role": "user", "content": user_input}
                ]
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=plan_messages
                )
                plan_text = response.choices[0].message.content
                print(f"\n📋 PLAN PROPUESTO:\n{'-'*40}\n{plan_text}\n{'-'*40}")
                
                approved = False
                while True:
                    resp = input("¿Aprobás este plan? (y / n / modify): ").strip().lower()
                    if resp in ('y', 'yes', 's', 'si', 'sí'):
                        print("✅ Plan aprobado. Ejecutando...")
                        approved = True
                        break
                    elif resp in ('n', 'no'):
                        print("❌ Plan rechazado. Tarea cancelada.")
                        break
                    elif resp == 'modify':
                        feedback = input("Ingresá tus modificaciones: ").strip()
                        print("⏳ Re-generando plan (simplificado para este demo)...")
                        user_input = f"{user_input}. Note: {feedback}"
                        break
                    else:
                        print("⚠️ Respuesta inválida.")
                
                if not approved and resp in ('n', 'no'):
                    tracer.flush()
                    continue

            # ORCHESTRATION PHASE
            state.status = "exploring"
            print("\n🔍 Fase 1: Exploración del repositorio")
            config["supervision_mode"] = supervision_mode
            explorer_result = run_subagent("explorer", user_input, state, config, tracer, trace, memory)
            if "NOT_ENOUGH_INFO" in explorer_result or "BLOCKED" in explorer_result:
                print("⚠️ Explorer reporta que falta información o está bloqueado.")
            
            state.status = "researching"
            print("\n📚 Fase 2: Investigación (RAG y Web)")
            config["supervision_mode"] = supervision_mode
            researcher_result = run_subagent("researcher", user_input, state, config, tracer, trace, memory)

            state.status = "implementing"
            print("\n🛠️ Fase 3: Implementación y Testing")
            
            # Save original file contents of workspace files for reviewer
            original_files = {}
            if WORKSPACE and os.path.exists(WORKSPACE):
                import glob
                for filepath in glob.glob(os.path.join(WORKSPACE, '**/*.kt'), recursive=True) + glob.glob(os.path.join(WORKSPACE, '**/*.kts'), recursive=True):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as file_obj:
                            original_files[filepath] = file_obj.read()
                    except Exception:
                        pass
            
            # Implementer / Tester loop
            max_retries = 3
            success = False
            for attempt in range(1, max_retries + 1):
                print(f"   ➤ Intento {attempt} de implementación...")
                if attempt > 1:
                    imp_task = f"{user_input}\n\nThe previous attempt failed testing. Please fix the code. Tester errors:\n{state.errors[-3:]}"
                imp_task = user_input
                    
                config["supervision_mode"] = supervision_mode  # Pasa el estado a las tools
                impl_result = run_subagent("implementer", imp_task, state, config, tracer, trace, memory)
                
                print("   ➤ Ejecutando tests...")
                config["supervision_mode"] = supervision_mode
                test_result = run_subagent("tester", "Run tests and verify the changes.", state, config, tracer, trace, memory)
                
                # Basic heuristic for success based on typical test outputs
                if ("PASSED" in test_result.upper() and "FAILED" not in test_result.upper()) or \
                   ("SUCCESS" in test_result.upper() and "ERROR" not in test_result.upper() and "EXCEPTION" not in test_result.upper()):
                     print("   ✅ Tests pasaron exitosamente.")
                     success = True
                     break
                else:
                    print(f"   ❌ Tests fallaron en el intento {attempt}.")
            
            if not success:
                print("⚠️ No se logró que los tests pasen después de los reintentos.")
            
            state.status = "reviewing"
            print("\n👀 Fase 4: Revisión de código")
            rev_task = f"{user_input}\n\nReview the changes. For context, these are some original files before changes (if modified):\n"
            for f in state.files_modified:
                if f in original_files:
                     rev_task += f"--- ORIGINAL {f} ---\n{original_files[f]}\n"
            
            config["supervision_mode"] = supervision_mode        
            reviewer_result = run_subagent("reviewer", rev_task, state, config, tracer, trace, memory)

            state.status = "completed"

            # GENERATE REPORT
            print("\n=================================================================")
            print("📝 REPORTE FINAL DE LA TAREA")
            print("=================================================================")
            print(f"Tarea: {user_input}")
            print(f"Archivos modificados: {', '.join(set(state.files_modified)) if state.files_modified else 'Ninguno'}")
            print("\nFuentes consultadas:")
            for src in state.sources_consulted:
                 print(f" - [{src['type']}] {src['ref']}")
            if state.errors:
                 print(f"\nErrores encontrados (últimos):")
                 for err in state.errors[-2:]:
                      print(f" - {err[:200]}...")
            print("\nResumen del Reviewer:")
            print(reviewer_result[:500] + ("..." if len(reviewer_result) > 500 else ""))
            print("=================================================================\n")

            # SAVE MEMORY
            print("💾 Guardando memoria del proyecto...")
            mem_summary_msgs = [
                {"role": "system", "content": "Extract architecture, important files, and commands from the following task state. Format as JSON with keys 'architecture', 'important_files' (dict), 'commands' (dict)."},
                {"role": "user", "content": state.to_summary()}
            ]
            try:
                mem_resp = client.chat.completions.create(model=MODEL, messages=mem_summary_msgs, response_format={"type": "json_object"})
                mem_data = json.loads(mem_resp.choices[0].message.content)
                if 'architecture' in mem_data: memory.update('architecture', mem_data['architecture'])
                if 'important_files' in mem_data: memory.update('important_files', mem_data['important_files'])
                if 'commands' in mem_data: memory.update('commands', mem_data['commands'])
                memory.save()
            except Exception as e:
                print(f"⚠️ Error actualizando memoria: {e}")

        except Exception as e:
            print(f"\n❌ Ocurrió un error inesperado durante la ejecución: {e}")
            traceback.print_exc()
        finally:
            print("🔌 Flushing observabilidad (Langfuse)...")
            tracer.flush()
