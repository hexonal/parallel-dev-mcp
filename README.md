# Parallel Development MCP - 完美融合架构

Claude Code的并行开发系统，采用优雅的四层FastMCP工具架构，基于最新FastMCP 2.11.3+，完全替代shell脚本。

## 🏗️ 完美融合架构

经过完美重构，项目现在采用清晰的四层分层架构，所有原mcp_server的能力都完美融合到mcp_tools中：

```
🎯 ORCHESTRATOR LAYER (编排层)
   └── 项目级编排和生命周期管理

📊 MONITORING LAYER (监控层)  
   └── 系统监控、诊断和状态仪表板

📋 SESSION LAYER (会话层)
   └── 细粒度会话管理和消息通信

🔧 TMUX LAYER (基础层)
   └── 纯MCP tmux会话编排
```

## 🏗️ 系统架构总览

### 整体架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         Claude Code IDE                         │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │   主会话 Master  │    │   子会话 Child   │                    │
│  │                │    │                │                    │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │                    │
│  │ │ Smart Hooks │ │    │ │ Smart Hooks │ │                    │
│  │ └─────────────┘ │    │ └─────────────┘ │                    │
│  └─────────────────┘    └─────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                    │                    │
            ┌───────▼────────┐   ┌───────▼────────┐
            │ smart_hooks.json│   │ smart_hooks.json│
            │   (统一配置)     │   │   (统一配置)     │
            └───────┬────────┘   └───────┬────────┘
                    │                    │
                    ▼                    ▼
        ┌─────────────────────────────────────────────┐
        │        Smart Session Detector               │
        │     (智能会话识别与通信系统)                   │
        │                                           │
        │  ┌─────────────┐  ┌─────────────────────┐ │
        │  │ 会话名称解析  │  │   自动会话发现        │ │
        │  └─────────────┘  └─────────────────────┘ │
        │  ┌─────────────┐  ┌─────────────────────┐ │
        │  │ 智能消息路由  │  │   通信协调管理        │ │
        │  └─────────────┘  └─────────────────────┘ │
        └─────────────────┬───────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────┐
    │                MCP 工具层架构                        │
    │                                                   │
    │ 🎯 ORCHESTRATOR   📊 MONITORING   📋 SESSION    🔧 TMUX │
    │    (3 tools)        (5 tools)      (7 tools)   (1 tool)│
    │                                                   │
    │ ┌───────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐ │
    │ │项目工作流编排  │ │系统健康监控  │ │会话消息管理  │ │会话编排 │ │
    │ │生命周期管理   │ │性能诊断分析  │ │关系注册维护  │ │基础操作 │ │
    │ │并行任务协调   │ │状态仪表板   │ │细粒度控制   │ │        │ │
    │ └───────────────┘ └─────────────┘ └─────────────┘ └────────┘ │
    └─────────────────────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────┐
    │                 Tmux 会话层                          │
    │                                                   │
    │  parallel_PROJECT_task_master    (主协调会话)       │
    │  ├── parallel_PROJECT_task_child_TASK1             │
    │  ├── parallel_PROJECT_task_child_TASK2             │
    │  └── parallel_PROJECT_task_child_TASK3             │
    │                                                   │
    │  🔄 自动消息传递  📊 状态同步  🎯 任务协调          │
    └─────────────────────────────────────────────────────┘
```

### 核心组件说明

#### 1. 智能会话识别系统 🧠
- **Smart Session Detector**: 核心智能引擎
- **会话名称解析**: 自动从tmux会话名提取项目和任务信息
- **自动会话发现**: 动态发现和连接相关会话
- **智能消息路由**: 自动建立主子会话通信链路

#### 2. 统一配置系统 ⚙️
- **smart_hooks.json**: 单一配置文件适用所有会话类型
- **零环境变量依赖**: 完全基于会话名称智能识别
- **动态适配**: 支持任意项目ID和任务ID组合

#### 3. 分层MCP工具架构 🏗️
```
🎯 ORCHESTRATOR LAYER (3工具)
├── orchestrate_project_workflow - 项目工作流编排
├── manage_project_lifecycle - 项目生命周期管理  
└── coordinate_parallel_tasks - 并行任务协调

📊 MONITORING LAYER (5工具)  
├── check_system_health - 系统健康检查
├── diagnose_session_issues - 会话问题诊断
├── get_performance_metrics - 性能指标获取
├── get_system_dashboard - 系统仪表板
└── generate_status_report - 状态报告生成

📋 SESSION LAYER (7工具)
├── create_development_session - 创建开发会话
├── send_message_to_session - 发送会话消息
├── get_session_messages - 获取会话消息
├── query_session_status - 查询会话状态
├── list_all_managed_sessions - 列出所有会话
├── register_session_relationship - 注册会话关系
└── get_session_hierarchy - 获取会话层级

🔧 TMUX LAYER (1工具)
└── tmux_session_orchestrator - 基础会话编排
```

#### 4. 会话命名与通信机制 📡
```
命名规范：
├── 主会话: parallel_{PROJECT_ID}_task_master
└── 子会话: parallel_{PROJECT_ID}_task_child_{TASK_ID}

通信流程：
├── 子会话启动 → 自动注册到主会话
├── 任务进度 → 自动汇报到主会话  
├── 状态同步 → 主会话维护全局状态
└── 会话完成 → 自动通知主会话
```

### 数据流向

```
用户操作 → Claude Code → Smart Hooks → 智能识别 → MCP工具 → Tmux会话
    ↑                                                        ↓
    └── 状态反馈 ← 消息汇报 ← 自动通信 ← 会话协调 ← 实际执行 ←┘
```

### 核心优势

1. **零配置复杂度**: 从N+1个配置文件简化到1个智能配置
2. **自动化程度高**: 智能识别、自动发现、自动通信
3. **可扩展性强**: 动态适配新项目和任务，无需修改配置
4. **可靠性高**: 基于实际tmux状态，避免配置不同步问题
5. **维护成本低**: 统一架构，清晰职责分离

## 🚀 快速开始

### 基础用户 - Tmux层
```bash
# 一键启动并行开发环境
uv run python -c "
from src.mcp_tools import tmux_session_orchestrator
result = tmux_session_orchestrator('init', 'ECOMMERCE', ['AUTH', 'PAYMENT', 'UI'])
print('✅ 项目初始化完成' if result else '❌ 初始化失败')
"

# 启动所有会话
uv run python -c "
from src.mcp_tools import tmux_session_orchestrator
tmux_session_orchestrator('start', 'ECOMMERCE', ['AUTH', 'PAYMENT', 'UI'])
"
```

### 高级用户 - Session层
```bash  
# 精细化会话管理
uv run python -c "
from src.mcp_tools import create_development_session, send_message_to_session

# 创建特定会话
create_development_session('ECOMMERCE', 'child', 'AUTH_TASK')

# 发送消息到会话
send_message_to_session('parallel_ECOMMERCE_task_child_AUTH', '请报告进度')
"
```

### 系统管理员 - Monitoring层
```bash
# 系统健康监控
uv run python -c "
from src.mcp_tools import check_system_health, get_system_dashboard

# 全面健康检查
health = check_system_health(include_detailed_metrics=True)
print('系统健康状态:', health)

# 获取监控仪表板
dashboard = get_system_dashboard(include_trends=True)
print('监控仪表板:', dashboard)
"
```

### 项目经理 - Orchestrator层
```bash
# 完整项目编排
uv run python -c "
from src.mcp_tools import orchestrate_project_workflow

# 编排完整项目工作流
result = orchestrate_project_workflow(
    project_id='ECOMMERCE',
    workflow_type='development', 
    tasks=['AUTH', 'PAYMENT', 'UI'],
    parallel_execution=True
)
print('工作流编排结果:', result)
"
```

## 🎯 核心功能

### 四层工具能力

| 层级 | 工具数量 | 主要功能 | 适用用户 |
|------|---------|----------|----------|
| **🔧 Tmux层** | 1个工具 | 纯MCP会话编排，零shell脚本 | 所有用户 |
| **📋 Session层** | 7个工具 | 细粒度会话管理和消息通信 | 高级用户 |  
| **📊 Monitoring层** | 5个工具 | 系统监控和诊断分析 | 系统管理员 |
| **🎯 Orchestrator层** | 3个工具 | 项目生命周期和工作流编排 | 项目经理 |

### 完整工具清单

<details>
<summary>点击查看全部16个MCP工具</summary>

#### 🔧 TMUX LAYER
- `tmux_session_orchestrator` - 基础会话编排

#### 📋 SESSION LAYER  
**会话管理**
- `create_development_session` - 创建开发会话
- `terminate_session` - 终止会话
- `query_session_status` - 查询会话状态  
- `list_all_managed_sessions` - 列出所有会话

**消息系统**
- `send_message_to_session` - 发送消息
- `get_session_messages` - 获取消息
- `mark_message_read` - 标记已读
- `broadcast_message` - 广播消息

**关系管理**
- `register_session_relationship` - 注册关系
- `query_child_sessions` - 查询子会话
- `get_session_hierarchy` - 获取层级结构

#### 📊 MONITORING LAYER
**健康监控**
- `check_system_health` - 系统健康检查
- `diagnose_session_issues` - 会话问题诊断
- `get_performance_metrics` - 性能指标

**状态仪表板**  
- `get_system_dashboard` - 系统仪表板
- `generate_status_report` - 状态报告
- `export_system_metrics` - 指标导出

#### 🎯 ORCHESTRATOR LAYER
- `orchestrate_project_workflow` - 项目工作流编排
- `manage_project_lifecycle` - 项目生命周期管理
- `coordinate_parallel_tasks` - 并行任务协调

</details>

## 📋 使用场景

### 电商项目示例

```python
# === 基础用户使用Tmux层 ===
tmux_session_orchestrator("start", "ECOMMERCE", ["AUTH", "PAYMENT", "UI"])

# === 高级用户使用Session层 ===  
# 精细控制每个会话
create_development_session("ECOMMERCE", "child", "AUTH")
send_message_to_session("parallel_ECOMMERCE_task_child_AUTH", "切换到OAuth实现")

# === 系统管理员使用Monitoring层 ===
# 监控系统健康
health = check_system_health()
dashboard = get_system_dashboard()

# === 项目经理使用Orchestrator层 ===
# 完整项目编排
orchestrate_project_workflow("ECOMMERCE", "development", ["AUTH", "PAYMENT", "UI"])
```

### 会话命名约定
- **主会话**: `parallel_{PROJECT_ID}_task_master`
- **子会话**: `parallel_{PROJECT_ID}_task_child_{TASK_ID}`
- **前缀匹配**: `parallel_{PROJECT_ID}_task_*`

## 🔧 架构优势

### ✅ 完美融合成果
- **零能力丢失**: 原mcp_server的所有功能都完美保留
- **架构清晰**: 四层分离，职责明确，易于理解和维护
- **向上兼容**: 上层工具自动调用下层，形成能力融合体系
- **用户友好**: 不同层级适配不同技能水平的用户

### ✅ 技术优势
- **纯MCP架构**: 完全消除shell脚本依赖
- **分层设计**: 每层专注特定职责，降低复杂度
- **工具原子性**: 每个函数都是独立MCP工具，可单独调用
- **智能编排**: 上层工具智能调用下层能力

### ✅ 运维优势
- **监控完善**: 专门的监控层提供全面的系统监控
- **诊断强大**: 深度会话问题诊断和性能分析
- **报告丰富**: 多格式状态报告和指标导出
- **清理彻底**: 完整的资源清理和会话管理

## 📁 项目结构

```
parallel-dev-mcp/
├── src/
│   ├── mcp_tools/               # 🏗️ 完美融合的四层MCP工具架构
│   │   ├── orchestrator/       # 🎯 ORCHESTRATOR层 - 项目编排(3工具)
│   │   ├── monitoring/         # 📊 MONITORING层 - 系统监控(5工具)
│   │   ├── session/            # 📋 SESSION层 - 会话管理(7工具)
│   │   └── tmux/               # 🔧 TMUX层 - 基础编排(1工具)
│   └── mcp_server/             # 底层组件支持(被tools调用)
├── examples/                   # 配置示例和智能hooks系统
│   └── hooks/                  # 🧠 智能会话识别系统
│       ├── smart_session_detector.py  # 核心智能引擎
│       └── README.md           # 智能系统详细文档
├── tools/                      # ⚙️ 智能配置生成工具
│   ├── config_generator.py     # 统一配置生成器
│   └── README.md              # 配置工具说明
├── docs/                       # 📚 详细文档
└── tests/                      # 🧪 测试套件

总计: 16个MCP工具 + 1个智能识别引擎 + 零shell脚本依赖
```

### 目录功能说明

#### src/mcp_tools/ - 核心MCP工具层
- **orchestrator/**: 项目级工作流编排、生命周期管理、并行协调
- **monitoring/**: 系统健康检查、性能监控、诊断分析、状态仪表板
- **session/**: 会话创建管理、消息通信、关系注册、层级维护
- **tmux/**: 基础tmux会话编排，统一入口工具

#### examples/hooks/ - 智能会话识别系统
- **smart_session_detector.py**: 核心智能引擎，自动会话识别与通信
- **零配置需求**: 基于会话名称的完全自动化识别

#### tools/ - 配置生成工具
- **config_generator.py**: 一键生成所有必要配置文件
- **智能化配置**: 生成统一的smart_hooks.json配置

#### 架构特点
- **分层清晰**: 四层架构，职责明确，向上兼容
- **智能集成**: hooks系统与MCP工具完美融合
- **零脚本依赖**: 完全消除shell脚本，纯MCP实现
- **统一配置**: 一个配置文件适配所有会话类型

## 📚 文档指南

- **新手用户**: 从Tmux层开始，使用 `tmux_session_orchestrator`
- **进阶用户**: 学习Session层的11个细粒度工具
- **运维人员**: 掌握Monitoring层的监控和诊断能力  
- **项目经理**: 使用Orchestrator层进行项目级管理

## 🧪 验证和测试

```bash
# 验证完整架构
uv run python -c "from src.parallel_dev_mcp import *; print('✅ 所有16个工具导入成功')"

# 测试基础功能
uv run python -c "
from src.parallel_dev_mcp import tmux_session_orchestrator
result = tmux_session_orchestrator('init', 'TEST', ['TASK1'])
print('✅ 基础功能正常' if result else '❌ 基础功能异常')
"

# 生成智能FastMCP服务器配置
uv run python tools/config_generator.py --project-id TEST --tasks TASK1 TASK2

# 启动FastMCP服务器
uv run python -m src.parallel_dev_mcp.server
```

## ⚡ 核心价值

### 🎯 **统一性**
四层架构统一了所有并行开发需求，从基础编排到项目级管理

### 🔧 **灵活性** 
用户可根据需求选择合适的层级，从简单到复杂全覆盖

### 📊 **可观测性**
专业的监控层提供完整的系统可观测性和问题诊断

### 🚀 **扩展性**
分层设计让系统具备出色的功能扩展和维护能力

---

**现在开始你的完美并行开发之旅！** 🚀

```bash
# 安装依赖并启动完整并行开发环境
uv sync
uv run python -c "
from src.mcp_tools import tmux_session_orchestrator
tmux_session_orchestrator('start', 'YOUR_PROJECT', ['TASK1', 'TASK2', 'TASK3'])
"
```

## 📋 MCP服务器集成与会话创建

### 关键设置：PROJECT_ID 与会话命名的强相关性

**重要**: MCP 配置中的 `PROJECT_ID` 环境变量必须与 tmux 会话名称保持一致！

### 第1步: 生成项目配置

```bash
# 生成项目配置
uv run python tools/config_generator.py --project-id YOUR_PROJECT --tasks TASK1 TASK2 TASK3

# 将生成的 claude-config.json 添加到 Claude Code 的 MCP 服务器配置中
```

### 第2步: 正确设置MCP服务器配置

在 Claude Code 中配置 MCP 服务器时，**必须确保** `PROJECT_ID` 环境变量与你的会话命名一致：

```json
{
  "mcpServers": {
    "parallel-dev-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.mcp_tools"],
      "cwd": "/path/to/parallel-dev-mcp",
      "env": {
        "PROJECT_ID": "YOUR_PROJECT",
        "PYTHONPATH": "/path/to/parallel-dev-mcp"
      }
    }
  }
}
```

⚠️ **关键**: `PROJECT_ID` 的值必须与你要创建的 tmux 会话名称匹配！

### 第3步: 创建对应的 tmux 会话

基于你设置的 `PROJECT_ID`，创建正确的 tmux 会话：

#### 方式1: 使用 MCP 工具创建（推荐）
```python
# 在 Claude Code 中执行，自动创建正确命名的会话
from src.mcp_tools import tmux_session_orchestrator

# 这会创建以下会话:
# - 主会话: parallel_YOUR_PROJECT_task_master  
# - 子会话: parallel_YOUR_PROJECT_task_child_TASK1
# - 子会话: parallel_YOUR_PROJECT_task_child_TASK2
# - 子会话: parallel_YOUR_PROJECT_task_child_TASK3
tmux_session_orchestrator("start", "YOUR_PROJECT", ["TASK1", "TASK2", "TASK3"])
```

#### 方式2: 手动创建 tmux 会话
如果你手动创建会话，**必须遵循命名规范**：

```bash
# 创建主会话（在此会话中启动 Claude Code）
tmux new-session -d -s "parallel_YOUR_PROJECT_task_master"

# 创建子会话（用于具体任务）
tmux new-session -d -s "parallel_YOUR_PROJECT_task_child_TASK1"
tmux new-session -d -s "parallel_YOUR_PROJECT_task_child_TASK2"
tmux new-session -d -s "parallel_YOUR_PROJECT_task_child_TASK3"
```

### 第4步: 验证配置正确性

```bash
# 检查会话是否正确创建
tmux list-sessions

# 应该看到类似输出:
# parallel_YOUR_PROJECT_task_master: 1 windows
# parallel_YOUR_PROJECT_task_child_TASK1: 1 windows  
# parallel_YOUR_PROJECT_task_child_TASK2: 1 windows
# parallel_YOUR_PROJECT_task_child_TASK3: 1 windows
```

### 命名规范总结

| 会话类型 | 命名格式 | 示例 |
|----------|----------|------|
| **主会话** | `parallel_{PROJECT_ID}_task_master` | `parallel_ECOMMERCE_task_master` |
| **子会话** | `parallel_{PROJECT_ID}_task_child_{TASK_ID}` | `parallel_ECOMMERCE_task_child_AUTH` |

**核心要点:**
- MCP 配置中的 `PROJECT_ID` = tmux 会话名称中的 `{PROJECT_ID}` 部分
- 智能hooks脚本通过解析会话名称自动提取 `PROJECT_ID` 进行匹配
- 只有命名正确的会话才能被智能系统识别和管理

### 智能Hooks配置
配置生成器同时生成智能hooks配置：

```json
{
  "user-prompt-submit-hook": {
    "command": ["python", "/path/to/smart_session_detector.py", "user-prompt", "{{prompt}}"],
    "description": "智能会话提示处理Hook - 自动识别会话类型"
  },
  "session-start-hook": {
    "command": ["python", "/path/to/smart_session_detector.py", "session-start"],
    "description": "智能会话启动Hook - 自动注册和协调"
  }
}
```

**关键特性：**
- 所有tmux会话共享同一个hooks配置文件
- 智能脚本根据会话名称自动判断会话类型
- 零配置需求，完全自动化的会话识别和通信

### 🚀 完整使用流程示例

以创建一个名为 "ECOMMERCE" 的电商项目为例：

#### 步骤1: 生成配置
```bash
python tools/config_generator.py --project-id ECOMMERCE --tasks AUTH PAYMENT UI
```

#### 步骤2: 配置 Claude Code MCP 服务器
将生成的配置添加到 Claude Code，确保 `PROJECT_ID` 设置为 `ECOMMERCE`：
```json
{
  "mcpServers": {
    "parallel-dev-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.mcp_tools"],
      "cwd": "/path/to/parallel-dev-mcp",
      "env": {
        "PROJECT_ID": "ECOMMERCE",
        "PYTHONPATH": "/path/to/parallel-dev-mcp"
      }
    }
  }
}
```

#### 步骤3: 配置智能 Hooks
将生成的 `smart_hooks.json` 配置到 Claude Code：
```bash
# 所有会话都使用这个配置文件
cat configs/smart_hooks.json
```

#### 步骤4: 创建和启动会话
```bash
# 方式A: 使用 MCP 工具自动创建（推荐）
# 在配置了 MCP 的 Claude Code 中执行：
# tmux_session_orchestrator("start", "ECOMMERCE", ["AUTH", "PAYMENT", "UI"])

# 方式B: 手动创建会话
tmux new-session -d -s "parallel_ECOMMERCE_task_master"
tmux new-session -d -s "parallel_ECOMMERCE_task_child_AUTH"  
tmux new-session -d -s "parallel_ECOMMERCE_task_child_PAYMENT"
tmux new-session -d -s "parallel_ECOMMERCE_task_child_UI"
```

#### 步骤5: 连接到会话并启动 Claude Code
```bash
# 连接到主会话
tmux attach-session -t parallel_ECOMMERCE_task_master
# 在主会话中启动 Claude Code（已配置 MCP 和 hooks）

# 在其他终端连接到子会话
tmux attach-session -t parallel_ECOMMERCE_task_child_AUTH
# 在子会话中启动 Claude Code（使用相同的 hooks 配置）
```

#### 步骤6: 验证智能识别工作
- **主会话启动时**: 看到 "🎯 Master会话启动: 项目 ECOMMERCE"
- **子会话启动时**: 看到 "🔧 Child会话启动: 项目 ECOMMERCE - 任务 AUTH" 和 "✅ 已注册到主会话"
- **任务进度时**: 子会话自动向主会话汇报进度
- **会话结束时**: 子会话自动向主会话发送完成通知

### ⚠️ 常见错误和解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| hooks不工作 | 会话名称不符合规范 | 确保使用 `parallel_{PROJECT_ID}_task_*` 格式 |
| 找不到主会话 | PROJECT_ID不匹配 | 检查MCP配置中的PROJECT_ID与会话名称是否一致 |
| 子会话无法注册 | 主会话不存在 | 确保先创建主会话再创建子会话 |
| 智能识别失败 | 会话名称解析错误 | 使用配置生成器生成的标准命名 |

## 🔗 配置和集成

### 智能 Claude Code Hooks 系统
革命性的零配置智能会话识别系统：

- **智能配置生成**: 使用 `tools/config_generator.py` 生成统一的智能hooks配置
- **自动会话识别**: `examples/hooks/smart_session_detector.py` 基于tmux会话名称自动识别会话类型
- **零环境变量依赖**: 完全基于会话名称模式匹配，无需预配置
- **统一配置文件**: 所有会话共享一个 `smart_hooks.json` 配置文件

#### 智能识别特性
- **配置文件减少80%**: 从N+1个文件简化到1个统一配置
- **自动会话发现**: 主会话自动发现和协调所有子会话
- **智能消息路由**: 基于会话名称的自动通信建立
- **动态适配**: 支持任意项目ID和任务ID组合

这种设计确保了 MCP 工具专注于会话管理核心功能，而智能配置系统提供了前所未有的简化体验。