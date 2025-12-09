# Java 详细规范参考

## 目录
- [JPA 规范](#jpa-规范)
- [事务管理](#事务管理)
- [测试规范](#测试规范)
- [日志规范](#日志规范)

---

## JPA 规范

### Entity 定义
```java
@Entity
@Table(name = "tasks")
@Getter
@Setter
@NoArgsConstructor
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
    private TaskStatus status = TaskStatus.PENDING;

    @Column(nullable = false)
    private Integer priority = 3;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;
}
```

### Repository 接口
```java
public interface TaskRepository extends JpaRepository<Task, String> {
    List<Task> findByStatus(TaskStatus status);

    @Query("SELECT t FROM Task t WHERE t.priority >= :minPriority")
    List<Task> findHighPriorityTasks(@Param("minPriority") Integer minPriority);

    @Query(value = "SELECT * FROM tasks WHERE status = :status", nativeQuery = true)
    List<Task> findByStatusNative(@Param("status") String status);
}
```

### 分页查询
```java
public Page<Task> findTasks(TaskFilter filter, Pageable pageable) {
    Specification<Task> spec = (root, query, cb) -> {
        List<Predicate> predicates = new ArrayList<>();

        if (filter.getStatus() != null) {
            predicates.add(cb.equal(root.get("status"), filter.getStatus()));
        }
        if (filter.getMinPriority() != null) {
            predicates.add(cb.greaterThanOrEqualTo(root.get("priority"), filter.getMinPriority()));
        }

        return cb.and(predicates.toArray(new Predicate[0]));
    };

    return taskRepository.findAll(spec, pageable);
}
```

---

## 事务管理

### 基本使用
```java
@Service
@RequiredArgsConstructor
public class TaskServiceImpl implements TaskService {
    private final TaskRepository taskRepository;

    @Transactional
    public Task create(CreateTaskDto dto) {
        Task task = new Task();
        task.setTitle(dto.title());
        task.setDescription(dto.description());
        return taskRepository.save(task);
    }

    @Transactional(readOnly = true)
    public Optional<Task> findById(String id) {
        return taskRepository.findById(id);
    }
}
```

### 事务传播
```java
// 默认：REQUIRED - 有则加入，无则创建
@Transactional(propagation = Propagation.REQUIRED)

// 强制新事务
@Transactional(propagation = Propagation.REQUIRES_NEW)

// 必须在已有事务中
@Transactional(propagation = Propagation.MANDATORY)
```

### 回滚规则
```java
// 指定回滚异常
@Transactional(rollbackFor = Exception.class)

// 排除回滚异常
@Transactional(noRollbackFor = BusinessException.class)
```

---

## 测试规范

### 单元测试
```java
@ExtendWith(MockitoExtension.class)
class TaskServiceImplTest {
    @Mock
    private TaskRepository taskRepository;

    @InjectMocks
    private TaskServiceImpl taskService;

    @Test
    void create_ShouldSaveTask() {
        // Given
        CreateTaskDto dto = new CreateTaskDto("Test Task", "Description", 3);
        Task savedTask = new Task();
        savedTask.setId("1");
        savedTask.setTitle(dto.title());

        when(taskRepository.save(any(Task.class))).thenReturn(savedTask);

        // When
        Task result = taskService.create(dto);

        // Then
        assertThat(result.getId()).isEqualTo("1");
        assertThat(result.getTitle()).isEqualTo("Test Task");
        verify(taskRepository).save(any(Task.class));
    }
}
```

### 集成测试
```java
@SpringBootTest
@Transactional
class TaskServiceIntegrationTest {
    @Autowired
    private TaskService taskService;

    @Autowired
    private TaskRepository taskRepository;

    @Test
    void create_ShouldPersistTask() {
        // Given
        CreateTaskDto dto = new CreateTaskDto("Integration Test", "Description", 3);

        // When
        Task result = taskService.create(dto);

        // Then
        assertThat(result.getId()).isNotNull();
        assertThat(taskRepository.findById(result.getId())).isPresent();
    }
}
```

### Controller 测试
```java
@WebMvcTest(TaskController.class)
class TaskControllerTest {
    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private TaskService taskService;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void getById_ShouldReturnTask() throws Exception {
        // Given
        TaskDto task = new TaskDto("1", "Test", "PENDING");
        when(taskService.findById("1")).thenReturn(Optional.of(task));

        // When & Then
        mockMvc.perform(get("/api/v1/tasks/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value("1"))
            .andExpect(jsonPath("$.title").value("Test"));
    }

    @Test
    void create_ShouldReturnCreated() throws Exception {
        // Given
        CreateTaskDto dto = new CreateTaskDto("New Task", "Description", 3);
        TaskDto created = new TaskDto("1", "New Task", "PENDING");
        when(taskService.create(any())).thenReturn(created);

        // When & Then
        mockMvc.perform(post("/api/v1/tasks")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(dto)))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.id").value("1"));
    }
}
```

---

## 日志规范

### Logger 使用
```java
@Slf4j
@Service
public class TaskServiceImpl implements TaskService {

    public Task create(CreateTaskDto dto) {
        log.info("Creating task: title={}", dto.title());

        try {
            Task task = doCreate(dto);
            log.info("Task created: id={}", task.getId());
            return task;
        } catch (Exception e) {
            log.error("Failed to create task: title={}", dto.title(), e);
            throw e;
        }
    }
}
```

### 日志级别
| 级别 | 用途 |
|------|------|
| ERROR | 错误，需要立即处理 |
| WARN | 警告，需要关注 |
| INFO | 重要业务操作 |
| DEBUG | 调试信息 |
| TRACE | 详细追踪 |

### 配置示例
```yaml
# application.yml
logging:
  level:
    root: INFO
    com.example: DEBUG
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n"
```
