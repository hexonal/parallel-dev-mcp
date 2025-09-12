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
send_message_to_session('child_ECOMMERCE_task_AUTH', '请报告进度')
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
| **📋 Session层** | 11个工具 | 细粒度会话管理和消息通信 | 高级用户 |  
| **📊 Monitoring层** | 6个工具 | 系统监控和诊断分析 | 系统管理员 |
| **🎯 Orchestrator层** | 3个工具 | 项目生命周期和工作流编排 | 项目经理 |

### 完整工具清单

<details>
<summary>点击查看全部21个MCP工具</summary>

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
send_message_to_session("child_ECOMMERCE_task_AUTH", "切换到OAuth实现")

# === 系统管理员使用Monitoring层 ===
# 监控系统健康
health = check_system_health()
dashboard = get_system_dashboard()

# === 项目经理使用Orchestrator层 ===
# 完整项目编排
orchestrate_project_workflow("ECOMMERCE", "development", ["AUTH", "PAYMENT", "UI"])
```

### 会话命名约定
- **主会话**: `master_project_{PROJECT_ID}`
- **子会话**: `child_{PROJECT_ID}_task_{TASK_ID}`

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
│   ├── mcp_tools/               # 完美融合的四层架构
│   │   ├── tmux/               # 🔧 Tmux层 - 基础编排
│   │   ├── session/            # 📋 Session层 - 细粒度管理  
│   │   ├── monitoring/         # 📊 Monitoring层 - 系统监控
│   │   └── orchestrator/       # 🎯 Orchestrator层 - 项目编排
│   └── mcp_server/             # 底层组件支持(被tools调用)
├── docs/                       # 详细文档
└── tests/                      # 测试套件
```

## 📚 文档指南

- **新手用户**: 从Tmux层开始，使用 `tmux_session_orchestrator`
- **进阶用户**: 学习Session层的11个细粒度工具
- **运维人员**: 掌握Monitoring层的监控和诊断能力  
- **项目经理**: 使用Orchestrator层进行项目级管理

## 🧪 验证和测试

```bash
# 验证完整架构
uv run python -c "from src.parallel_dev_mcp import *; print('✅ 所有21个工具导入成功')"

# 测试基础功能
uv run python -c "
from src.parallel_dev_mcp import tmux_session_orchestrator
result = tmux_session_orchestrator('init', 'TEST', ['TASK1'])
print('✅ 基础功能正常' if result else '❌ 基础功能异常')
"

# 生成FastMCP服务器配置
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

## 📋 MCP服务器集成

使用配置生成器为Claude Code创建MCP服务器配置：

```bash
# 生成项目配置
uv run python tools/config_generator.py --project-id YOUR_PROJECT --tasks TASK1 TASK2 TASK3

# 将生成的 claude-config.json 添加到 Claude Code 的 MCP 服务器配置中
```

生成的配置示例：
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