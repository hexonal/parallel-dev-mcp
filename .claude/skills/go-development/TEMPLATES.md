# Go 代码模板

## 目录
- [包注释模板](#包注释模板)
- [结构体模板](#结构体模板)
- [接口模板](#接口模板)
- [Service 模板](#service-模板)
- [Handler 模板](#handler-模板)
- [Repository 模板](#repository-模板)

---

## 包注释模板

```go
// Package task
//
// 任务管理模块
//
// @author {{通过 MCP Git 自动获取}}
// @date   {{通过 MCP DateTime 自动获取}}
// @description 任务的创建、调度、执行管理
package task
```

---

## 结构体模板

### Model 结构体
```go
// Task 任务定义
type Task struct {
    ID          string    `json:"id" gorm:"primaryKey"`
    Title       string    `json:"title" gorm:"not null"`
    Description string    `json:"description"`
    Status      string    `json:"status" gorm:"default:pending"`
    Priority    int       `json:"priority" gorm:"default:3"`
    CreatedAt   time.Time `json:"created_at"`
    UpdatedAt   time.Time `json:"updated_at"`
}
```

### 请求结构体
```go
// CreateTaskReq 创建任务请求
type CreateTaskReq struct {
    Title       string `json:"title" binding:"required,min=1,max=200"`
    Description string `json:"description" binding:"max=1000"`
    Priority    int    `json:"priority" binding:"min=1,max=5"`
}

// UpdateTaskReq 更新任务请求
type UpdateTaskReq struct {
    Title       *string `json:"title" binding:"omitempty,min=1,max=200"`
    Description *string `json:"description" binding:"omitempty,max=1000"`
    Status      *string `json:"status" binding:"omitempty,oneof=pending running completed failed"`
    Priority    *int    `json:"priority" binding:"omitempty,min=1,max=5"`
}
```

### 响应结构体
```go
// TaskResp 任务响应
type TaskResp struct {
    ID          string `json:"id"`
    Title       string `json:"title"`
    Description string `json:"description"`
    Status      string `json:"status"`
    Priority    int    `json:"priority"`
    CreatedAt   string `json:"created_at"`
}

// ListResp 列表响应
type ListResp[T any] struct {
    Items []T   `json:"items"`
    Total int64 `json:"total"`
    Page  int   `json:"page"`
    Size  int   `json:"size"`
}
```

---

## 接口模板

### Repository 接口
```go
// TaskRepository 任务数据访问接口
type TaskRepository interface {
    Create(ctx context.Context, task *Task) error
    GetByID(ctx context.Context, id string) (*Task, error)
    List(ctx context.Context, filter *TaskFilter) ([]*Task, int64, error)
    Update(ctx context.Context, task *Task) error
    Delete(ctx context.Context, id string) error
}
```

### Service 接口
```go
// TaskService 任务服务接口
type TaskService interface {
    Create(ctx context.Context, req *CreateTaskReq) (*Task, error)
    GetByID(ctx context.Context, id string) (*Task, error)
    List(ctx context.Context, filter *TaskFilter) (*ListResp[*Task], error)
    Update(ctx context.Context, id string, req *UpdateTaskReq) error
    Delete(ctx context.Context, id string) error
}
```

---

## Service 模板

```go
// service/task.go
package service

import (
    "context"
    "fmt"
    "log/slog"
    "time"

    "github.com/google/uuid"
)

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

// Create 创建任务
func (s *taskServiceImpl) Create(ctx context.Context, req *CreateTaskReq) (*Task, error) {
    // 1. 构建任务对象
    task := &Task{
        ID:          uuid.New().String(),
        Title:       req.Title,
        Description: req.Description,
        Priority:    req.Priority,
        Status:      "pending",
        CreatedAt:   time.Now(),
    }

    // 2. 保存到数据库
    if err := s.repo.Create(ctx, task); err != nil {
        return nil, fmt.Errorf("create task: %w", err)
    }

    // 3. 记录日志
    s.log.Info("task created", "id", task.ID, "title", task.Title)

    return task, nil
}

// GetByID 获取任务
func (s *taskServiceImpl) GetByID(ctx context.Context, id string) (*Task, error) {
    task, err := s.repo.GetByID(ctx, id)
    if err != nil {
        return nil, fmt.Errorf("get task %s: %w", id, err)
    }
    return task, nil
}
```

---

## Handler 模板

```go
// handler/task.go
package handler

import (
    "net/http"

    "github.com/gin-gonic/gin"
)

type TaskHandler struct {
    service TaskService
}

// NewTaskHandler 创建任务处理器
func NewTaskHandler(service TaskService) *TaskHandler {
    return &TaskHandler{service: service}
}

// Create 创建任务
// @Summary 创建任务
// @Tags Task
// @Accept json
// @Produce json
// @Param req body CreateTaskReq true "创建请求"
// @Success 201 {object} TaskResp
// @Router /tasks [post]
func (h *TaskHandler) Create(c *gin.Context) {
    // 1. 绑定请求
    var req CreateTaskReq
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }

    // 2. 调用服务
    task, err := h.service.Create(c.Request.Context(), &req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }

    // 3. 返回响应
    c.JSON(http.StatusCreated, toTaskResp(task))
}

// GetByID 获取任务
// @Summary 获取任务详情
// @Tags Task
// @Produce json
// @Param id path string true "任务ID"
// @Success 200 {object} TaskResp
// @Router /tasks/{id} [get]
func (h *TaskHandler) GetByID(c *gin.Context) {
    id := c.Param("id")

    task, err := h.service.GetByID(c.Request.Context(), id)
    if err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "task not found"})
        return
    }

    c.JSON(http.StatusOK, toTaskResp(task))
}
```

---

## Repository 模板

```go
// repository/task.go
package repository

import (
    "context"
    "fmt"

    "gorm.io/gorm"
)

type taskRepositoryImpl struct {
    db *gorm.DB
}

// NewTaskRepository 创建任务仓库
func NewTaskRepository(db *gorm.DB) TaskRepository {
    return &taskRepositoryImpl{db: db}
}

// Create 创建任务
func (r *taskRepositoryImpl) Create(ctx context.Context, task *Task) error {
    if err := r.db.WithContext(ctx).Create(task).Error; err != nil {
        return fmt.Errorf("insert task: %w", err)
    }
    return nil
}

// GetByID 根据ID获取任务
func (r *taskRepositoryImpl) GetByID(ctx context.Context, id string) (*Task, error) {
    var task Task
    if err := r.db.WithContext(ctx).First(&task, "id = ?", id).Error; err != nil {
        return nil, fmt.Errorf("find task: %w", err)
    }
    return &task, nil
}

// List 获取任务列表
func (r *taskRepositoryImpl) List(ctx context.Context, filter *TaskFilter) ([]*Task, int64, error) {
    var tasks []*Task
    var total int64

    query := r.db.WithContext(ctx).Model(&Task{})

    // 1. 应用过滤条件
    if filter.Status != "" {
        query = query.Where("status = ?", filter.Status)
    }

    // 2. 统计总数
    if err := query.Count(&total).Error; err != nil {
        return nil, 0, fmt.Errorf("count tasks: %w", err)
    }

    // 3. 分页查询
    offset := (filter.Page - 1) * filter.Size
    if err := query.Offset(offset).Limit(filter.Size).Find(&tasks).Error; err != nil {
        return nil, 0, fmt.Errorf("find tasks: %w", err)
    }

    return tasks, total, nil
}
```
