# 配置示例和工具

这个目录包含配置示例和用户工具，用于设置和管理parallel-dev-mcp系统。

## 📁 目录结构

```
examples/
├── hooks/                  # Claude hooks配置示例
│   ├── master_session_hooks.json    # 主会话hooks示例
│   ├── child_session_hooks.json     # 子会话hooks示例
│   └── hooks_manager.py             # Hooks配置管理工具
└── config/                 # Claude配置示例（预留）
```

## 🔧 配置工具

### 1. 项目配置生成 (tools/config_generator.py)

```bash
# 使用配置生成器
python tools/config_generator.py --project-id MYPROJECT --tasks AUTH PAYMENT UI

# 生成的配置文件：
# - claude-config.json (Claude MCP服务器配置)
# - master_hooks.json (主会话hooks)
# - child_*_hooks.json (各任务的子会话hooks)
```

### 2. Hooks配置管理 (examples/hooks/hooks_manager.py)

```bash
# 安装hooks到Claude Code
python examples/hooks/hooks_manager.py --install --project-id MYPROJECT

# 生成自定义hooks配置
python examples/hooks/hooks_manager.py --generate --sessions master,child_AUTH
```

## 📋 使用流程

### 1. 生成配置文件
```bash
python tools/config_generator.py --project-id ECOMMERCE --tasks AUTH PAYMENT UI
```

### 2. 使用MCP工具启动
```python
from src.mcp_tools import tmux_session_orchestrator

# 初始化项目（仅创建目录）
tmux_session_orchestrator("init", "ECOMMERCE", ["AUTH", "PAYMENT", "UI"])

# 启动会话
tmux_session_orchestrator("start", "ECOMMERCE", ["AUTH", "PAYMENT", "UI"])
```

### 3. 连接到会话
```bash
# 主会话
tmux attach-session -t master_project_ECOMMERCE

# 子会话
tmux attach-session -t child_ECOMMERCE_task_AUTH
```

## ⚙️ 配置说明

### MCP服务器配置
MCP工具需要在Claude Code中配置MCP服务器：

```json
{
  "mcpServers": {
    "tmux-orchestrator": {
      "command": "python",
      "args": ["-m", "src.mcp_tools.tmux_session_orchestrator"],
      "env": {
        "PROJECT_ID": "YOUR_PROJECT"
      }
    }
  }
}
```

### Hooks配置示例
Hooks用于自动化会话行为：

- **master_session_hooks.json**: 主会话hooks配置示例
- **child_session_hooks.json**: 子会话hooks配置示例  
- **hooks_manager.py**: 用于生成和安装自定义hooks配置

## 🎯 设计原则

1. **分离关注点**: 配置生成是用户工具，不是核心MCP功能
2. **纯MCP架构**: 核心工具专注于会话管理
3. **用户友好**: 提供示例和工具简化配置过程
4. **灵活配置**: 用户可以自定义配置而不依赖内置生成器

## 📚 更多信息

- 核心MCP工具文档：`src/mcp_tools/README.md`
- 项目整体文档：`README.md`
- Claude Code集成：`CLAUDE.md`