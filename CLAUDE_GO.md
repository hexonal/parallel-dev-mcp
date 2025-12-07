# CLAUDE_GO.md

This file provides guidance to Claude Code (claude.ai/code) when working with Go code in this repository.

对话的时候，始终使用的是中文

## 本项目为 Go 项目，采用 Go 1.23.0+ 完成开发迭代
- 技术版本：Go 1.23.0, Gin Web 框架, GORM ORM
- 尽可能采用 Go 1.23+ 的优秀特性开发

## 🚨 严格开发规范 (2025最新标准)
              
## 🎯 核心设计原则

### 1. YAGNI 原则（You Aren't Gonna Need It）
- ✅ 只实现当前需要的功能

### 接口架构严格标准

#### HTTP方法严格限制
**🔴 强制要求**：
- **业务接口**: 所有业务逻辑接口**有且仅**接受POST请求
- **严格禁止**: RESTful风格的GET/PUT/DELETE用于业务逻辑

### 代码质量严格标准

#### 方法长度严格限制

#### 方法长度严格限制
**🔴 强制要求**：
- **所有方法**: 不得超过50行（包含注释和空行）
- **超长处理**: 必须拆分为多个 private 方法或使用设计模式
- **设计模式**: 优先使用 Template Method、Strategy、Factory 模式
- **注释规范**: 禁止使用行尾注释，所有注释必须独立成行
- **方法注释**: 每个方法必须在方法签名前添加注释，格式为 /** ... */，包含功能说明、参数说明、返回值说明
- **步骤注释**: 方法体内部代码必须逐步编号注释（如 // 1. 初始化参数、// 2. 执行核心逻辑），覆盖所有逻辑步骤

  - 规则：
  - 每行或每个逻辑步骤，都要写编号注释（// 1. 或 # 1.）。
  - 注释说明的是“做什么”，而不是简单重复代码。

  - 适用于 Go 语言的标准开发模式。

    - Go 版本（`//` 注释）
```go
// 函数：${METHOD_NAME}
// 描述：${METHOD_DESCRIPTION}
func ${METHOD_NAME}() error {
    // 1. 初始化参数或对象

    // 2. 校验输入数据

    // 3. 执行核心逻辑

    // 4. 处理结果（如保存、返回、输出）

    // 5. 记录日志 / 异常处理

    // 6. 返回最终结果
    return nil
}
```
📖 **使用规范**：

* 第 1 行：方法名说明。
* 第 2 行：方法作用描述。
* 每个逻辑步骤用 **数字编号**（保持 1 → N 顺序）。
* 如果步骤内部有多行代码，可以在每行继续加 `//` 解释。

#### 类型安全严格标准

**🔴 严格禁止**：

- `map[string]interface{}` - 严禁在任何场景使用
- `interface{}` 参数 - 严禁作为方法参数或返回值
- **替代方案**: 必须创建类型安全的专用结构体(struct)

#### 推荐使用的Go结构体标签

**核心标签**:

- `json` - JSON序列化/反序列化标签
- `gorm` - GORM数据库映射标签
- `binding` - Gin框架参数绑定验证标签
- `validate` - 参数验证标签

**常用标签示例**:

```go
type User struct {
    ID       uint   `json:"id" gorm:"primaryKey;autoIncrement"`
    Name     string `json:"name" gorm:"not null" binding:"required" validate:"min=2,max=50"`
    Email    string `json:"email" gorm:"unique;not null" binding:"required,email"`
    Age      int    `json:"age" binding:"min=1,max=150"`
}
```

#### 结构体设计严格标准
**🔴 强制要求**：
- **最小化原则**: 避免创建过多结构体，优先复用现有结构体
- **严禁嵌套**: 请求/响应结构体内不允许嵌套其他复杂对象
- **扁平化设计**: 所有请求/响应结构体必须是扁平结构
- **命名规范**: Request后缀为Req，Response后缀为Resp

#### Go包注释严格标准
**🔴 强制要求**：
- **作者信息**: 通过MCP Git集成自动获取，严禁手动设置
- **时间信息**: 通过MCP DateTime集成自动获取
- **注释格式**: 标准化包注释包含author、date、description
- **文档规范**: 遵循Go标准的godoc注释规范

#### Service层严格标准
**🔴 强制要求**：
- **Interface+Implementation模式**: 所有Service必须有接口和实现结构体
- **依赖注入**: 使用Wire进行依赖注入，避免手动实例化
- **结构体拷贝规范**: 使用统一的结构体拷贝工具或手动映射
- **错误处理**: 统一使用pkg/errors包进行错误包装和处理

#### 外部集成严格标准
**🔴 强制要求**：
- **Context7+DeepWiki**: 用于研究正确的Go 1.23+ 和遇到问题时候的开发方式
- **Go Modules**: 严格使用Go Modules进行依赖管理
- **第三方库**: 优先使用成熟稳定的第三方库，如Gin、GORM、Wire等

### 编译和部署严格标准

#### 编译成功强制要求
**🔴 强制要求**：
- **必须成功**: 必须在项目根目录下执行 `go build` 或 `make build` 成功
- **无失败测试**: 所有单元测试必须通过 `go test ./...`
- **无编译警告**: 消除所有编译警告和错误
- **代码格式化**: 使用 `go fmt` 和 `goimports` 进行代码格式化
- **静态检查**: 使用 `go vet` 和 `golangci-lint` 进行代码质量检查

### 禁用功能清单
**❌ 明确删除**：
- **过度复杂化**: 避免引入不必要的企业级特性
- **DDD设计**: 禁用领域驱动设计，采用简单三层架构
- **map[string]interface{}**: 任何场景下都禁止使用
- **interface{}参数**: 禁止作为函数参数或返回值
- **行尾注释**: 所有注释必须独立成行
- **嵌套结构体**: 请求/响应结构体必须扁平化，禁止嵌套复杂对象
- **过度设计模式**: 避免为了模式而模式
- **panic的滥用**: 只在真正不可恢复的错误中使用panic



### MCP工具集成
项目集成了以下MCP工具以提供增强功能：
- **sequential-thinking**: 复杂问题分析和决策支持
- **context7**: 技术文档和API查询
- **deepwiki**: 深度技术知识查询
- **git-config**: Git仓库配置管理
- **mcp-datetime**: 时间戳生成
- **yapi-auto-mcp**: API文档自动化
- **其他的 mcp 均按需使用**

## 常用命令

### 构建和打包
```bash
# 构建项目
go build -o callback-server ./main.go

# 使用Makefile构建
make build

# 跳过测试进行编译
go build -tags skiptest -o callback-server ./main.go

# 清理构建产物
make clean

# 运行测试
go test ./...

# 代码格式化
go fmt ./...
goimports -w .

# 静态检查
go vet ./...
golangci-lint run
```


## 架构概览
 通过 init 命令让其更新





## MCP工具集成开发

#### 自动化类注解生成

**MCP Git集成**：

- 自动获取Git用户信息作为author
- 自动获取提交时间作为创建时间
- 禁止手动设置作者和时间信息

**MCP DateTime集成**：

- 自动生成标准时间戳
- 支持多种日期格式
- 用于类创建时间字段
              
##### **标准类代码注释模板**：

### 🟨 Go 模板
```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 模块
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 功能实现
package ${PACKAGE_NAME}

// ${NAME} 结构体
type ${NAME} struct {
    // 字段定义
}
```

```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 接口
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 接口定义
package ${PACKAGE_NAME}

// ${NAME} 接口
type ${NAME} interface {
    // 方法定义
}

```

```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 枚举常量
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 枚举
package ${PACKAGE_NAME}

const (
    ${NAME}A = iota
    ${NAME}B
    ${NAME}C
)
```

```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 错误类型
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 自定义错误
package ${PACKAGE_NAME}

import "fmt"

// ${NAME} 错误
type ${NAME} struct {
    msg string
}

func (e *${NAME}) Error() string {
    return fmt.Sprintf("${NAME} error: %s", e.msg)
}

```