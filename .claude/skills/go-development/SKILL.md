---
name: go-development
description: Go 开发规范 - Go 1.23+ 最佳实践、Gin/GORM 框架、并发模式。用于 .go 文件、Go 后端项目。
triggers:
  - Go
  - Golang
  - go.mod
  - gin
  - gorm
  - .go
---

# Go Development Skill

Go 1.23+ 开发规范，涵盖 Gin Web 框架、GORM ORM、并发模式等最佳实践。

## 快速参考

**详细规范**: 见 [REFERENCE.md](REFERENCE.md)
**代码模板**: 见 [TEMPLATES.md](TEMPLATES.md)

---

## 核心原则

| 原则 | 要求 |
|------|------|
| **YAGNI** | 只实现当前需要的功能 |
| **KISS** | 采用简单三层架构，禁用 DDD |
| **单一职责** | 每个包/结构体只做一件事 |

---

## 强制规则

### 代码行数限制
| 类型 | 最大行数 |
|------|----------|
| 方法 | 50 行 |
| 文件 | 500 行 |

### 注释规范
```go
// 正确：注释独立成行
// 函数：ProcessTask
// 描述：处理单个任务
func ProcessTask(task *Task) error {
    // 1. 验证任务
    // 2. 执行逻辑
    // 3. 返回结果
}

// 禁止：行尾注释
func ProcessTask(task *Task) error { // 处理任务
```

### 类型安全
```go
// 正确：使用具体类型
type TaskResult struct {
    ID     string `json:"id"`
    Status string `json:"status"`
}

// 禁止：使用 interface{} 或 map[string]interface{}
func GetResult() map[string]interface{} // 严禁！
```

---

## 项目结构

```
project/
├── cmd/                    # 入口点
│   └── server/main.go
├── internal/               # 私有包
│   ├── handler/            # HTTP 处理器
│   ├── service/            # 业务逻辑
│   ├── repository/         # 数据访问
│   └── model/              # 数据模型
├── pkg/                    # 公共包
│   ├── errors/
│   └── utils/
├── configs/
├── go.mod
└── go.sum
```

---

## 命名规范速查

| 类型 | 规范 | 示例 |
|------|------|------|
| 包名 | 小写单词 | `task`, `worker` |
| 局部变量 | 短命名 | `i`, `n`, `err` |
| 包级变量 | 描述性 | `maxRetries`, `defaultTimeout` |
| 结构体 | PascalCase | `TaskResult`, `WorkerConfig` |
| 请求结构体 | +Req 后缀 | `CreateTaskReq` |
| 响应结构体 | +Resp 后缀 | `CreateTaskResp` |
| 单方法接口 | 方法名+er | `Reader`, `Writer`, `Executor` |
| 多方法接口 | 描述性名称 | `TaskManager`, `WorkerPool` |

---

## 结构体设计

### 标签使用
```go
type User struct {
    ID     uint   `json:"id" gorm:"primaryKey"`
    Name   string `json:"name" gorm:"not null" binding:"required"`
    Email  string `json:"email" gorm:"unique" binding:"required,email"`
    Status int    `json:"status" gorm:"default:1"`
}
```

### 扁平化设计
```go
// 正确：扁平结构
type CreateTaskReq struct {
    Title       string `json:"title" binding:"required"`
    Description string `json:"description"`
    Priority    int    `json:"priority" binding:"min=1,max=5"`
}

// 禁止：嵌套结构
type CreateTaskReq struct {
    Task    Task    `json:"task"`     // 禁止！
    Options Options `json:"options"`  // 禁止！
}
```

---

## 错误处理

### 错误包装
```go
func ProcessTask(taskID string) error {
    task, err := getTask(taskID)
    if err != nil {
        return fmt.Errorf("get task %s: %w", taskID, err)
    }
    return nil
}
```

### 禁止 panic 滥用
- 只在真正不可恢复的错误中使用
- HTTP Handler 中绝对不能 panic

---

## 禁用功能清单

- `map[string]interface{}` - 任何场景禁止
- `interface{}` 参数 - 禁止作为函数参数/返回值
- 行尾注释 - 所有注释必须独立成行
- 嵌套结构体 - 请求/响应必须扁平化
- DDD 设计 - 采用简单三层架构
- panic 滥用 - 只在不可恢复错误中使用

---

## 常用命令

```bash
# 构建
go build -o app ./cmd/server

# 测试
go test ./...
go test -cover ./...

# 格式化
go fmt ./...
goimports -w .

# 静态检查
go vet ./...
golangci-lint run

# 依赖
go mod tidy
```

---

## MCP 工具集成

| 工具 | 用途 |
|------|------|
| sequential-thinking | 架构设计、复杂问题分析 |
| context7 | Go/Gin/GORM 官方文档查询 |
| deepwiki | Go 生态、开源库文档 |
| git-config | Git 用户信息获取 |
| mcp-datetime | 时间戳生成 |

---

## 检查清单

- [ ] 方法 < 50 行
- [ ] 无 `interface{}` 类型
- [ ] 无 `map[string]interface{}`
- [ ] 无行尾注释
- [ ] 请求/响应扁平化
- [ ] 错误正确包装
- [ ] 接口命名以 er 结尾

---

## 参考文档

- **[REFERENCE.md](REFERENCE.md)** - Service 层、并发模式、测试规范
- **[TEMPLATES.md](TEMPLATES.md)** - 完整代码模板
