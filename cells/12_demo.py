import os

# Create Demo Project Cell

DEMO_DIR = config.get("workspace", "./workspace/demo-spring-app")

directories = [
    "src/main/kotlin/com/demo/model",
    "src/main/kotlin/com/demo/repository",
    "src/main/kotlin/com/demo/service",
    "src/main/kotlin/com/demo/controller",
    "src/test/kotlin/com/demo/service"
]

for d in directories:
    os.makedirs(os.path.join(DEMO_DIR, d), exist_ok=True)

build_gradle_content = """plugins {
    kotlin("jvm") version "1.9.22"
    kotlin("plugin.spring") version "1.9.22"
    id("org.springframework.boot") version "3.2.2"
    id("io.spring.dependency-management") version "1.1.4"
}

group = "com.demo"
version = "0.0.1-SNAPSHOT"

java {
    sourceCompatibility = JavaVersion.VERSION_17
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}

tasks.withType<Test> {
    useJUnitPlatform()
}
"""

settings_gradle_content = 'rootProject.name = "demo-spring-app"\n'

app_kt_content = """package com.demo

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class DemoApplication

fun main(args: Array<String>) {
    runApplication<DemoApplication>(*args)
}
"""

task_kt_content = """package com.demo.model

data class Task(
    val id: Long? = null,
    val title: String,
    val description: String = "",
    val completed: Boolean = false
)
"""

repo_kt_content = """package com.demo.repository

import com.demo.model.Task
import org.springframework.stereotype.Repository

@Repository
class TaskRepository {
    private val tasks = mutableMapOf<Long, Task>()
    private var nextId = 1L

    fun save(task: Task): Task {
        val saved = task.copy(id = task.id ?: nextId++)
        tasks[saved.id!!] = saved
        return saved
    }

    fun findById(id: Long): Task? = tasks[id]

    fun findAll(): List<Task> = tasks.values.toList()

    fun deleteById(id: Long) {
        tasks.remove(id)
    }
}
"""

service_kt_content = """package com.demo.service

import com.demo.model.Task
import com.demo.repository.TaskRepository
import org.springframework.stereotype.Service

@Service
class TaskService(private val repository: TaskRepository) {
    
    fun createTask(title: String, description: String = ""): Task {
        // BUG 3: No validation - allows empty title
        return repository.save(Task(title = title, description = description))
    }

    fun getTask(id: Long): Task {
        // BUG 1: Unsafe !! operator - will throw NPE if task not found
        return repository.findById(id)!!
    }

    fun getAllTasks(): List<Task> = repository.findAll()

    fun deleteTask(id: Long) = repository.deleteById(id)
}
"""

controller_kt_content = """package com.demo.controller

import com.demo.model.Task
import com.demo.service.TaskService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/tasks")
class TaskController(private val taskService: TaskService) {

    @GetMapping
    fun getAll(): ResponseEntity<List<Task>> = ResponseEntity.ok(taskService.getAllTasks())

    @GetMapping("/{id}")
    fun getById(@PathVariable id: Long): ResponseEntity<Task> = ResponseEntity.ok(taskService.getTask(id))

    @PostMapping
    fun create(@RequestBody request: CreateTaskRequest): ResponseEntity<Task> {
        val task = taskService.createTask(request.title, request.description)
        // BUG 2: Should return 201 Created, not 200 OK
        return ResponseEntity.ok(task)
    }
}

data class CreateTaskRequest(val title: String, val description: String = "")
"""

test_kt_content = """package com.demo.service

import com.demo.repository.TaskRepository
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

class TaskServiceTest {
    private lateinit var repository: TaskRepository
    private lateinit var service: TaskService

    @BeforeEach
    fun setup() {
        repository = TaskRepository()
        service = TaskService(repository)
    }

    @Test
    fun `createTask should create a task with valid title`() {
        val task = service.createTask("Test Task", "Description")
        assertEquals("Test Task", task.title)
        assertNotNull(task.id)
    }

    @Test
    fun `getTask should return null-safe result for non-existent id`() {
        val exception = assertThrows<Exception> { service.getTask(999) }
        // We expect a specific domain exception or NullPointerException to be handled properly, 
        // not a raw Kotlin NullPointerException from the !! operator.
        assertFalse(exception is NullPointerException, "Should not throw raw NullPointerException")
    }

    @Test
    fun `createTask should reject empty title`() {
        // This test WILL FAIL due to BUG 3 (no validation)
        assertThrows<IllegalArgumentException> { service.createTask("") }
    }
}
"""

def write_demo_file(path, content):
    with open(os.path.join(DEMO_DIR, path), "w", encoding="utf-8") as f:
        f.write(content)

write_demo_file("build.gradle.kts", build_gradle_content)
write_demo_file("settings.gradle.kts", settings_gradle_content)
write_demo_file("src/main/kotlin/com/demo/DemoApplication.kt", app_kt_content)
write_demo_file("src/main/kotlin/com/demo/model/Task.kt", task_kt_content)
write_demo_file("src/main/kotlin/com/demo/repository/TaskRepository.kt", repo_kt_content)
write_demo_file("src/main/kotlin/com/demo/service/TaskService.kt", service_kt_content)
write_demo_file("src/main/kotlin/com/demo/controller/TaskController.kt", controller_kt_content)
write_demo_file("src/test/kotlin/com/demo/service/TaskServiceTest.kt", test_kt_content)

print(f"✅ Proyecto de demostración creado en: {DEMO_DIR}")
print("Contiene 3 bugs intencionales para que el agente los resuelva.")

# Change working directory so that commands run in the workspace context
os.chdir(DEMO_DIR)
print(f"CWD actualizado a: {os.getcwd()}")
