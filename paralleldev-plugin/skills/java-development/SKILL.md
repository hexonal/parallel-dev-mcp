---
name: java-development
description: Java 开发规范 - JDK 17+ 最佳实践、Spring Boot 3.x、Record/Pattern Matching。用于 .java 文件、Spring 项目。
triggers:
  - Java
  - Spring
  - Maven
  - Gradle
  - .java
  - SpringBoot
---

# Java Development Skill

JDK 17+ 开发规范，涵盖 Spring Boot 3.x、Records、Pattern Matching、Sealed Classes 等现代特性。

## 快速参考

**详细规范**: 见 [REFERENCE.md](REFERENCE.md)
**代码模板**: 见 [TEMPLATES.md](TEMPLATES.md)

---

## 核心原则

| 原则 | 要求 |
|------|------|
| **YAGNI** | 只实现当前需要的功能 |
| **KISS** | 采用简单三层架构 |
| **单一职责** | 每个类只做一件事 |

---

## 强制规则

### 代码行数限制
| 类型 | 最大行数 |
|------|----------|
| 方法 | 50 行 |
| 类 | 500 行 |

### JDK 17+ 特性优先
```java
// 正确：使用 Record 替代 POJO
public record TaskDto(
    String id,
    String title,
    String status
) {}

// 避免：传统 POJO
public class TaskDto {
    private String id;
    private String title;
    // getter/setter...
}
```

### Pattern Matching
```java
// 正确：使用 Pattern Matching
if (obj instanceof Task task) {
    process(task.getId());
}

// 正确：switch Pattern Matching
return switch (status) {
    case "pending" -> TaskStatus.PENDING;
    case "running" -> TaskStatus.RUNNING;
    case "completed" -> TaskStatus.COMPLETED;
    default -> throw new IllegalArgumentException("Unknown status");
};
```

### Sealed Classes
```java
// 正确：使用 Sealed Classes 限制继承
public sealed interface TaskResult
    permits SuccessResult, FailureResult {}

public record SuccessResult(String output) implements TaskResult {}
public record FailureResult(String error) implements TaskResult {}
```

---

## 项目结构

```
project/
├── src/main/java/com/example/
│   ├── controller/         # REST 控制器
│   ├── service/            # 业务逻辑
│   │   └── impl/
│   ├── repository/         # 数据访问
│   ├── entity/             # JPA 实体
│   ├── dto/                # 数据传输对象 (Records)
│   ├── config/             # 配置类
│   └── exception/          # 异常处理
├── src/main/resources/
│   ├── application.yml
│   └── application-dev.yml
├── src/test/java/
├── pom.xml / build.gradle
└── README.md
```

---

## 命名规范速查

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `TaskService`, `UserController` |
| 方法名 | camelCase | `createTask`, `findById` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 包名 | 小写 | `com.example.task` |
| DTO | +Dto 后缀 | `TaskDto`, `CreateTaskDto` |
| Entity | 无后缀 | `Task`, `User` |
| Repository | +Repository | `TaskRepository` |
| Service | +Service | `TaskService` |
| Controller | +Controller | `TaskController` |

---

## Spring Boot 3.x 规范

### 依赖注入
```java
// 正确：构造函数注入
@Service
@RequiredArgsConstructor
public class TaskServiceImpl implements TaskService {
    private final TaskRepository taskRepository;
    private final TaskMapper taskMapper;
}

// 避免：字段注入
@Autowired
private TaskRepository taskRepository;
```

### REST Controller
```java
@RestController
@RequestMapping("/api/v1/tasks")
@RequiredArgsConstructor
public class TaskController {
    private final TaskService taskService;

    @GetMapping("/{id}")
    public ResponseEntity<TaskDto> getById(@PathVariable String id) {
        return taskService.findById(id)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<TaskDto> create(@Valid @RequestBody CreateTaskDto dto) {
        TaskDto created = taskService.create(dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }
}
```

### 异常处理
```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(EntityNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(EntityNotFoundException e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(new ErrorResponse(404, e.getMessage()));
    }
}

public record ErrorResponse(int code, String message) {}
```

---

## 禁用功能清单

- 传统 POJO (使用 Record 替代)
- 字段注入 @Autowired (使用构造函数注入)
- 原始类型参数 (使用包装类)
- 手写 getter/setter (使用 Lombok 或 Record)
- 裸 try-catch (使用 @ControllerAdvice)
- System.out.println (使用 SLF4J Logger)

---

## 常用命令

```bash
# Maven
mvn clean install
mvn spring-boot:run
mvn test

# Gradle
./gradlew clean build
./gradlew bootRun
./gradlew test
```

---

## MCP 工具集成

| 工具 | 用途 |
|------|------|
| sequential-thinking | 架构设计、复杂问题分析 |
| context7 | Spring/JPA 官方文档查询 |
| deepwiki | Java 生态、开源库文档 |
| git-config | Git 用户信息获取 |
| mcp-datetime | 时间戳生成 |

---

## 检查清单

- [ ] 方法 < 50 行
- [ ] 使用 Record 替代 POJO
- [ ] 使用构造函数注入
- [ ] Pattern Matching 简化类型判断
- [ ] 无 System.out.println
- [ ] 全局异常处理
- [ ] SLF4J Logger

---

## 参考文档

- **[REFERENCE.md](REFERENCE.md)** - JPA、事务、测试规范
- **[TEMPLATES.md](TEMPLATES.md)** - 完整代码模板
