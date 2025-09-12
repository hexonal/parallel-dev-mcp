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
2. **master_hooks.json** - 主会话hooks配置
3. **child_*_hooks.json** - 各子会话hooks配置
4. **project_metadata.json** - 项目元数据

### 设计原则

- **用户工具**: 这是用户层面的配置工具，不是core MCP功能
- **分离关注点**: 配置生成与会话管理分离
- **灵活配置**: 用户可以自定义配置模板和输出

### 与MCP工具集成

生成配置后，使用core MCP工具启动项目：

```python
from src.mcp_tools import tmux_session_orchestrator

# 1. 初始化项目（创建目录结构）
tmux_session_orchestrator("init", "MYPROJECT", ["TASK1", "TASK2"])

# 2. 启动会话
tmux_session_orchestrator("start", "MYPROJECT", ["TASK1", "TASK2"])
```

## 🎯 与core MCP工具的区别

| 方面 | Core MCP工具 | 配置工具 |
|------|-------------|----------|
| **职责** | 会话管理 | 配置文件生成 |
| **位置** | `src/mcp_tools/` | `tools/` |
| **用户** | Claude直接调用 | 开发者手动使用 |
| **依赖** | 纯MCP架构 | 独立工具脚本 |

这种分离确保了core MCP工具的纯净性，专注于会话管理核心功能。