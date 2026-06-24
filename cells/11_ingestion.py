# RAG Ingestion Cell

KOTLIN_NULL_SAFETY = """
# Kotlin Null Safety
Kotlin's type system is aimed at eliminating the danger of null references, also known as The Billion Dollar Mistake.
- Nullable types: String? can hold null, String cannot.
- Safe calls: `b?.length` returns length if b is not null, otherwise null.
- Elvis operator: `val l = b?.length ?: -1` provides a default value (-1) if the expression to the left is null.
- Not-null assertion operator: `b!!` converts any value to a non-null type and throws NullPointerException if the value is null. Use this sparingly!
- Safe casts: `a as? Int` returns null if the cast is unsuccessful.
- `let` function: `listWithNulls.forEach { it?.let { println(it) } }` executes the block only if `it` is not null.
"""

KOTLIN_DATA_CLASSES = """
# Kotlin Data Classes
Data classes are mainly used to store state.
`data class User(val name: String, val age: Int)`
Compiler automatically derives the following members from all properties declared in the primary constructor:
- equals()/hashCode() pair
- toString() of the form "User(name=John, age=42)"
- componentN() functions corresponding to the properties in their order of declaration
- copy() function: `val jack = user.copy(name = "Jack")`
To exclude a property from the generated implementations, declare it inside the class body instead of the primary constructor.
"""

KOTLIN_BASICS = """
# Kotlin Basics
- when expression: Replaces the switch operator.
  ```kotlin
  when (x) {
      1 -> print("x == 1")
      2 -> print("x == 2")
      else -> { print("x is neither 1 nor 2") }
  }
  ```
- Extension functions: Provides the ability to extend a class with new functionality without having to inherit from the class.
  `fun String.removeFirstLastChar(): String = this.substring(1, this.length - 1)`
- Sealed classes: Represent restricted class hierarchies. All direct subclasses of a sealed class are known at compile time.
- Companion objects: If you need to write a function that can be called without having a class instance but needs access to the internals of a class, you can write it as a member of a companion object declaration inside that class.
"""

SPRING_BOOT_REST = """
# Spring Boot REST Controllers
- `@RestController`: Combines @Controller and @ResponseBody.
- Mapping annotations: `@GetMapping("/path")`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`.
- Extracting values:
  - `@PathVariable`: Extracts values from the URI path (e.g., `/api/users/{id}`).
  - `@RequestParam`: Extracts query parameters (e.g., `/api/users?name=john`).
  - `@RequestBody`: Binds the HTTP request body to a domain object.
- `ResponseEntity`: Represents the entire HTTP response (status code, headers, and body).
  - Return `ResponseEntity.ok(body)` for 200 OK.
  - Return `ResponseEntity.created(locationURI).body(body)` for 201 Created.
  - Return `ResponseEntity.notFound().build()` for 404 Not Found.
"""

SPRING_BOOT_DI = """
# Spring Boot Dependency Injection
- Stereotype annotations: `@Component`, `@Service`, `@Repository`, `@Controller`. These tell Spring to manage the class as a bean.
- Constructor Injection: The recommended way to inject dependencies, especially in Kotlin.
  ```kotlin
  @Service
  class UserService(private val userRepository: UserRepository) { ... }
  ```
- `@Autowired`: Optional for constructor injection if there's only one constructor. Used for field or setter injection (less preferred).
- `@Configuration` & `@Bean`: Used to explicitly declare beans in a configuration class.
"""

SPRING_DATA_JPA = """
# Spring Data JPA
- Repositories: Interface extending `CrudRepository<T, ID>` or `JpaRepository<T, ID>`.
- Query derivation: Create queries by defining method names (e.g., `findByLastName(lastName: String)`).
- Custom queries: Use `@Query("SELECT u FROM User u WHERE u.status = ?1")`.
- Entity: Mark domain classes with `@Entity`.
- IDs: Use `@Id` and `@GeneratedValue(strategy = GenerationType.IDENTITY)` for auto-incrementing primary keys.
"""

SPRING_BOOT_TESTING = """
# Spring Boot Testing
- `@SpringBootTest`: Loads the complete application context for integration testing.
- `@WebMvcTest(UserController::class)`: Test slice for testing only the web layer (controllers).
- `MockMvc`: Used to perform HTTP requests and assert responses in web tests.
- `@MockBean` (or `@MockkBean` if using MockK): Replaces a bean in the context with a mock.
- JUnit 5: Use `@Test`, `@BeforeEach`, `@AfterEach`.
- Assertions: `assertEquals(expected, actual)`, `assertNotNull(value)`, `assertThrows<Exception> { ... }`.
"""

GRADLE_KOTLIN_DSL = """
# Gradle Kotlin DSL
Structure of build.gradle.kts:
- `plugins { kotlin("jvm") version "1.9"; id("org.springframework.boot") version "3.2.0" }`
- `dependencies { implementation("org.springframework.boot:spring-boot-starter-web"); testImplementation("org.springframework.boot:spring-boot-starter-test") }`
- Dependencies configurations: `implementation` (required at compile and runtime), `testImplementation` (required only for tests).
"""

SPRING_VALIDATION = """
# Spring Validation
- Add dependency: `spring-boot-starter-validation`.
- Annotations on DTOs: `@NotBlank` (must not be null and must contain at least one non-whitespace character), `@NotNull`, `@Size(min=2, max=30)`, `@Pattern`.
- Trigger validation: Use `@Valid` on the `@RequestBody` parameter in the controller.
- Exception handling: If validation fails, a `MethodArgumentNotValidException` is thrown, which translates to a 400 Bad Request.
"""

print("📚 Iniciando ingesta de documentación en RAG...")

docs_to_ingest = [
    (KOTLIN_NULL_SAFETY, "Kotlin Docs - Null Safety"),
    (KOTLIN_DATA_CLASSES, "Kotlin Docs - Data Classes"),
    (KOTLIN_BASICS, "Kotlin Docs - Basics"),
    (SPRING_BOOT_REST, "Spring Docs - REST API"),
    (SPRING_BOOT_DI, "Spring Docs - Dependency Injection"),
    (SPRING_DATA_JPA, "Spring Docs - Data JPA"),
    (SPRING_BOOT_TESTING, "Spring Docs - Testing"),
    (GRADLE_KOTLIN_DSL, "Gradle Docs - Kotlin DSL"),
    (SPRING_VALIDATION, "Spring Docs - Validation")
]

for doc_text, source_name in docs_to_ingest:
    ingest_document(doc_text, source_name)

print(f"✅ Ingesta completada. Se indexaron {len(docs_to_ingest)} documentos principales.")
if rag_collection:
    print(f"📊 Total de chunks en ChromaDB: {rag_collection.count()}")
