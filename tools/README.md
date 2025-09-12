# 配置工具

这个目录包含用户配置工具，用于生成Claude Code和hooks配置文件。

## 🔧 config_generator.py

配置生成工具，从core MCP工具中分离出来，作为用户层面的配置工具。

### 使用方法

```bash
# 生成项目配置
python tools/config_generator.py --project-id MYPROJECT --tasks TASK1 TASK2 TASK3

# 指定输出目录
python tools/config_generator.py --project-id MYPROJECT --tasks AUTH PAYMENT --output-dir ./my_configs
```

### 生成的配置文件

1. **claude-config.json** - Claude Code MCP服务器配置
2. **smart_hooks.json** - 智能会话hooks配置（统一处理所有会话类型）
3. **project_metadata.json** - 项目元数据
4. **start_commands.json** - Claude启动命令

### 设计原则

- **用户工具**: 这是用户层面的配置工具，不是core MCP功能
- **分离关注点**: 配置生成与会话管理分离
- **智能配置**: 生成零配置需求的智能hooks系统
- **灵活配置**: 用户可以自定义配置模板和输出

### 智能Hooks特性

- **零配置管理**: 生成的hooks配置适用于所有会话类型
- **自动会话识别**: 基于tmux会话名称的智能识别系统
- **统一配置文件**: 所有会话共享同一个 `smart_hooks.json`
- **动态适配**: 支持任意项目和任务组合，无需预配置

### 与MCP工具集成

生成配置后，使用core MCP工具启动项目：

```python
from src.mcp_tools import tmux_session_orchestrator

# 1. 初始化项目（自动生成智能hooks配置）
tmux_session_orchestrator("init", "MYPROJECT", ["TASK1", "TASK2"])

# 2. 启动会话（所有会话自动使用智能hooks）
tmux_session_orchestrator("start", "MYPROJECT", ["TASK1", "TASK2"])
```

### 智能配置工作流

```bash
# 第1步: 生成配置（包含智能hooks）
python tools/config_generator.py --project-id ECOMMERCE --tasks AUTH API UI

# 第2步: 查看生成的智能配置
cat configs/smart_hooks.json

# 第3步: 在Claude Code中配置hooks
# 所有会话都使用同一个smart_hooks.json文件

# 第4步: 启动项目会话
python -c "from src.mcp_tools import tmux_session_orchestrator; tmux_session_orchestrator('start', 'ECOMMERCE', ['AUTH', 'API', 'UI'])"
```

### 智能识别演示

```bash
# 会话启动时的自动识别过程：

# 主会话: parallel_ECOMMERCE_task_master  
# → 智能脚本识别为主会话
# → 自动扫描相关子会话
# → 显示: "🎯 Master会话启动: 项目 ECOMMERCE"

# 子会话: parallel_ECOMMERCE_task_child_AUTH
# → 智能脚本识别为子会话  
# → 自动注册到主会话
# → 显示: "🔧 Child会话启动: 项目 ECOMMERCE - 任务 AUTH"
# → 显示: "✅ 已注册到主会话: parallel_ECOMMERCE_task_master"
```

## 🎯 与core MCP工具的区别

| 方面 | Core MCP工具 | 智能配置工具 |
|------|-------------|-------------|
| **职责** | 会话管理 | 智能配置生成 |
| **位置** | `src/mcp_tools/` | `tools/` + `examples/hooks/` |
| **用户** | Claude直接调用 | 开发者手动使用 |
| **依赖** | 纯MCP架构 | 独立工具脚本 |
| **Hooks支持** | 使用智能hooks | 生成智能hooks |
| **配置复杂度** | 零配置 | 一键生成 |

### 智能化优势

| 特性 | 传统方案 | 智能配置方案 |
|------|----------|-------------|
| **配置文件数量** | N+1个 | 1个 |
| **维护成本** | 高（每个任务需要独立配置） | 低（一次配置全局适用） |
| **扩展性** | 差（添加任务需要新配置） | 优（动态适配新任务） |
| **可靠性** | 中等（依赖环境变量） | 高（基于实际tmux状态） |
| **学习成本** | 高（需要理解多个配置） | 低（零配置使用） |

这种分离确保了core MCP工具的纯净性，专注于会话管理核心功能，而智能配置系统提供了前所未有的简化体验。