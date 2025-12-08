# Java 代码模板

## 目录
- [Record 模板](#record-模板)
- [Entity 模板](#entity-模板)
- [Controller 模板](#controller-模板)
- [Service 模板](#service-模板)
- [Repository 模板](#repository-模板)
- [配置模板](#配置模板)

---

## Record 模板

### DTO Record
```java
// dto/TaskDto.java
public record TaskDto(
    String id,
    String title,
    String description,
    String status,
    Integer priority,
    LocalDateTime createdAt
) {
    // 静态工厂方法
    public static TaskDto from(Task entity) {
        return new TaskDto(
            entity.getId(),
            entity.getTitle(),
            entity.getDescription(),
            entity.getStatus().name(),
            entity.getPriority(),
            entity.getCreatedAt()
        );
    }
}
```

### 请求 Record
```java
// dto/CreateTaskDto.java
public record CreateTaskDto(
    @NotBlank(message = "Title is required")
    @Size(max = 200, message = "Title must be less than 200 characters")
    String title,

    @Size(max = 1000, message = "Description must be less than 1000 characters")
    String description,

    @Min(value = 1, message = "Priority must be at least 1")
    @Max(value = 5, message = "Priority must be at most 5")
    Integer priority
) {
    // 默认值构造
    public CreateTaskDto {
        if (priority == null) {
            priority = 3;
        }
    }
}
```

### 响应 Record
```java
// dto/PageResponse.java
public record PageResponse<T>(
    List<T> items,
    long total,
    int page,
    int size,
    int totalPages
) {
    public static <T> PageResponse<T> from(Page<T> page) {
        return new PageResponse<>(
            page.getContent(),
            page.getTotalElements(),
            page.getNumber(),
            page.getSize(),
            page.getTotalPages()
        );
    }
}
```

---

## Entity 模板

```java
// entity/Task.java
@Entity
@Table(name = "tasks")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Task {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private String id;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(length = 1000)
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    @Builder.Default
    private TaskStatus status = TaskStatus.PENDING;

    @Column(nullable = false)
    @Builder.Default
    private Integer priority = 3;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;
}

// entity/TaskStatus.java
public enum TaskStatus {
    PENDING,
    RUNNING,
    COMPLETED,
    FAILED
}
```

---

## Controller 模板

```java
// controller/TaskController.java
@RestController
@RequestMapping("/api/v1/tasks")
@RequiredArgsConstructor
@Slf4j
public class TaskController {
    private final TaskService taskService;

    @GetMapping
    public ResponseEntity<PageResponse<TaskDto>> list(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String status) {

        Pageable pageable = PageRequest.of(page, size, Sort.by("createdAt").descending());
        Page<TaskDto> result = taskService.findAll(status, pageable);

        return ResponseEntity.ok(PageResponse.from(result));
    }

    @GetMapping("/{id}")
    public ResponseEntity<TaskDto> getById(@PathVariable String id) {
        return taskService.findById(id)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<TaskDto> create(@Valid @RequestBody CreateTaskDto dto) {
        log.info("Creating task: {}", dto.title());
        TaskDto created = taskService.create(dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<TaskDto> update(
            @PathVariable String id,
            @Valid @RequestBody UpdateTaskDto dto) {
        return taskService.update(id, dto)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable String id) {
        taskService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
```

---

## Service 模板

```java
// service/TaskService.java
public interface TaskService {
    Page<TaskDto> findAll(String status, Pageable pageable);
    Optional<TaskDto> findById(String id);
    TaskDto create(CreateTaskDto dto);
    Optional<TaskDto> update(String id, UpdateTaskDto dto);
    void delete(String id);
}

// service/impl/TaskServiceImpl.java
@Service
@RequiredArgsConstructor
@Slf4j
public class TaskServiceImpl implements TaskService {
    private final TaskRepository taskRepository;

    @Override
    @Transactional(readOnly = true)
    public Page<TaskDto> findAll(String status, Pageable pageable) {
        Page<Task> page = status != null
            ? taskRepository.findByStatus(TaskStatus.valueOf(status), pageable)
            : taskRepository.findAll(pageable);

        return page.map(TaskDto::from);
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<TaskDto> findById(String id) {
        return taskRepository.findById(id).map(TaskDto::from);
    }

    @Override
    @Transactional
    public TaskDto create(CreateTaskDto dto) {
        Task task = Task.builder()
            .title(dto.title())
            .description(dto.description())
            .priority(dto.priority())
            .build();

        Task saved = taskRepository.save(task);
        log.info("Task created: id={}", saved.getId());

        return TaskDto.from(saved);
    }

    @Override
    @Transactional
    public Optional<TaskDto> update(String id, UpdateTaskDto dto) {
        return taskRepository.findById(id)
            .map(task -> {
                if (dto.title() != null) task.setTitle(dto.title());
                if (dto.description() != null) task.setDescription(dto.description());
                if (dto.priority() != null) task.setPriority(dto.priority());
                return TaskDto.from(taskRepository.save(task));
            });
    }

    @Override
    @Transactional
    public void delete(String id) {
        taskRepository.deleteById(id);
        log.info("Task deleted: id={}", id);
    }
}
```

---

## Repository 模板

```java
// repository/TaskRepository.java
public interface TaskRepository extends JpaRepository<Task, String> {

    Page<Task> findByStatus(TaskStatus status, Pageable pageable);

    List<Task> findByPriorityGreaterThanEqual(Integer priority);

    @Query("SELECT t FROM Task t WHERE t.status = :status AND t.priority >= :priority")
    List<Task> findByStatusAndMinPriority(
        @Param("status") TaskStatus status,
        @Param("priority") Integer priority
    );

    @Modifying
    @Query("UPDATE Task t SET t.status = :status WHERE t.id = :id")
    int updateStatus(@Param("id") String id, @Param("status") TaskStatus status);
}
```

---

## 配置模板

### application.yml
```yaml
spring:
  application:
    name: task-service

  datasource:
    url: jdbc:postgresql://localhost:5432/taskdb
    username: ${DB_USERNAME:postgres}
    password: ${DB_PASSWORD:postgres}
    driver-class-name: org.postgresql.Driver

  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: false
    properties:
      hibernate:
        format_sql: true
        dialect: org.hibernate.dialect.PostgreSQLDialect

server:
  port: 8080

logging:
  level:
    root: INFO
    com.example: DEBUG
```

### 异常处理配置
```java
// exception/GlobalExceptionHandler.java
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
            .map(FieldError::getDefaultMessage)
            .collect(Collectors.joining(", "));

        return ResponseEntity.badRequest()
            .body(new ErrorResponse(400, message));
    }

    @ExceptionHandler(EntityNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(EntityNotFoundException e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(new ErrorResponse(404, e.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGeneral(Exception e) {
        log.error("Unexpected error", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(new ErrorResponse(500, "Internal server error"));
    }
}

public record ErrorResponse(int code, String message) {}
```
