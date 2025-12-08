# Go 详细规范参考

## 目录
- [Service 层规范](#service-层规范)
- [错误处理详细](#错误处理详细)
- [并发模式](#并发模式)
- [测试规范](#测试规范)

---

## Service 层规范

### Interface + Implementation 模式
```go
// service/task.go

// TaskService 任务服务接口
type TaskService interface {
    Create(ctx context.Context, req *CreateTaskReq) (*Task, error)
    GetByID(ctx context.Context, id string) (*Task, error)
    List(ctx context.Context, filter *TaskFilter) ([]*Task, error)
    Update(ctx context.Context, id string, req *UpdateTaskReq) error
    Delete(ctx context.Context, id string) error
}

// taskServiceImpl 任务服务实现
type taskServiceImpl struct {
    repo TaskRepository
    log  *slog.Logger
}

// NewTaskService 创建任务服务
func NewTaskService(repo TaskRepository, log *slog.Logger) TaskService {
    return &taskServiceImpl{
        repo: repo,
        log:  log,
    }
}
```

### Service 方法实现
```go
// Create 创建任务
func (s *taskServiceImpl) Create(ctx context.Context, req *CreateTaskReq) (*Task, error) {
    // 1. 验证请求
    if err := validateCreateTaskReq(req); err != nil {
        return nil, fmt.Errorf("validate request: %w", err)
    }

    // 2. 构建任务对象
    task := &Task{
        ID:          uuid.New().String(),
        Title:       req.Title,
        Description: req.Description,
        Priority:    req.Priority,
        Status:      TaskStatusPending,
        CreatedAt:   time.Now(),
    }

    // 3. 保存到数据库
    if err := s.repo.Create(ctx, task); err != nil {
        return nil, fmt.Errorf("create task: %w", err)
    }

    // 4. 返回结果
    return task, nil
}
```

---

## 错误处理详细

### 自定义错误类型
```go
// pkg/errors/errors.go

type TaskError struct {
    TaskID  string
    Message string
    Cause   error
}

func (e *TaskError) Error() string {
    if e.Cause != nil {
        return fmt.Sprintf("task %s: %s: %v", e.TaskID, e.Message, e.Cause)
    }
    return fmt.Sprintf("task %s: %s", e.TaskID, e.Message)
}

func (e *TaskError) Unwrap() error {
    return e.Cause
}
```

### 错误包装链
```go
func ProcessTask(taskID string) error {
    // 1. 获取任务
    task, err := getTask(taskID)
    if err != nil {
        return fmt.Errorf("get task %s: %w", taskID, err)
    }

    // 2. 验证任务
    if err := validateTask(task); err != nil {
        return fmt.Errorf("validate task: %w", err)
    }

    // 3. 执行任务
    if err := executeTask(task); err != nil {
        return fmt.Errorf("execute task: %w", err)
    }

    return nil
}
```

### HTTP 错误响应
```go
// handler/error.go

type ErrorResp struct {
    Code    int    `json:"code"`
    Message string `json:"message"`
}

func HandleError(c *gin.Context, err error) {
    var taskErr *TaskError
    if errors.As(err, &taskErr) {
        c.JSON(http.StatusBadRequest, ErrorResp{
            Code:    400,
            Message: taskErr.Message,
        })
        return
    }

    c.JSON(http.StatusInternalServerError, ErrorResp{
        Code:    500,
        Message: "internal server error",
    })
}
```

---

## 并发模式

### Goroutine + Channel
```go
func ProcessTasksConcurrently(tasks []*Task) []error {
    // 1. 创建结果通道
    errCh := make(chan error, len(tasks))
    var wg sync.WaitGroup

    // 2. 并发处理任务
    for _, task := range tasks {
        wg.Add(1)
        go func(t *Task) {
            defer wg.Done()
            if err := processTask(t); err != nil {
                errCh <- err
            }
        }(task)
    }

    // 3. 等待所有任务完成
    wg.Wait()
    close(errCh)

    // 4. 收集错误
    var errs []error
    for err := range errCh {
        errs = append(errs, err)
    }

    return errs
}
```

### Context 超时控制
```go
func ExecuteWithTimeout(ctx context.Context, task *Task) error {
    // 1. 创建超时 context
    ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
    defer cancel()

    // 2. 创建结果通道
    done := make(chan error, 1)

    // 3. 异步执行
    go func() {
        done <- executeTask(ctx, task)
    }()

    // 4. 等待完成或超时
    select {
    case err := <-done:
        return err
    case <-ctx.Done():
        return ctx.Err()
    }
}
```

### Worker Pool 模式
```go
func WorkerPool(ctx context.Context, tasks <-chan *Task, workers int) <-chan error {
    errCh := make(chan error, workers)
    var wg sync.WaitGroup

    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for task := range tasks {
                if err := processTask(ctx, task); err != nil {
                    errCh <- err
                }
            }
        }()
    }

    go func() {
        wg.Wait()
        close(errCh)
    }()

    return errCh
}
```

---

## 测试规范

### 表驱动测试
```go
func TestProcessTask(t *testing.T) {
    tests := []struct {
        name    string
        task    *Task
        wantErr bool
        errMsg  string
    }{
        {
            name:    "valid task",
            task:    &Task{ID: "1", Title: "Test"},
            wantErr: false,
        },
        {
            name:    "nil task",
            task:    nil,
            wantErr: true,
            errMsg:  "task is nil",
        },
        {
            name:    "empty title",
            task:    &Task{ID: "2", Title: ""},
            wantErr: true,
            errMsg:  "title is required",
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := ProcessTask(tt.task)
            if tt.wantErr {
                if err == nil {
                    t.Error("expected error, got nil")
                }
                if tt.errMsg != "" && !strings.Contains(err.Error(), tt.errMsg) {
                    t.Errorf("expected error containing %q, got %q", tt.errMsg, err.Error())
                }
            } else if err != nil {
                t.Errorf("unexpected error: %v", err)
            }
        })
    }
}
```

### Mock 接口
```go
// mock/task_service.go

type MockTaskService struct {
    CreateFunc  func(ctx context.Context, req *CreateTaskReq) (*Task, error)
    GetByIDFunc func(ctx context.Context, id string) (*Task, error)
}

func (m *MockTaskService) Create(ctx context.Context, req *CreateTaskReq) (*Task, error) {
    if m.CreateFunc != nil {
        return m.CreateFunc(ctx, req)
    }
    return nil, nil
}

func (m *MockTaskService) GetByID(ctx context.Context, id string) (*Task, error) {
    if m.GetByIDFunc != nil {
        return m.GetByIDFunc(ctx, id)
    }
    return nil, nil
}
```

### 测试 HTTP Handler
```go
func TestCreateTaskHandler(t *testing.T) {
    // 1. 创建 mock service
    mockService := &MockTaskService{
        CreateFunc: func(ctx context.Context, req *CreateTaskReq) (*Task, error) {
            return &Task{ID: "1", Title: req.Title}, nil
        },
    }

    // 2. 创建 handler
    handler := NewTaskHandler(mockService)

    // 3. 创建测试请求
    body := `{"title": "Test Task"}`
    req := httptest.NewRequest(http.MethodPost, "/tasks", strings.NewReader(body))
    req.Header.Set("Content-Type", "application/json")

    // 4. 记录响应
    w := httptest.NewRecorder()

    // 5. 创建 gin context 并执行
    c, _ := gin.CreateTestContext(w)
    c.Request = req
    handler.Create(c)

    // 6. 验证结果
    if w.Code != http.StatusCreated {
        t.Errorf("expected status %d, got %d", http.StatusCreated, w.Code)
    }
}
```
