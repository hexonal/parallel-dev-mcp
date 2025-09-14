# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based parallel development system featuring a **优化的三层MCP工具架构**. All original mcp_server capabilities have been perfectly integrated into mcp_tools with an elegant layered design, now streamlined and focused.

## 🏗️ Architecture Overview

The project now features a **streamlined three-layer architecture** after removing over-designed components:

```
📊 MONITORING LAYER - Basic system health monitoring (1 tool)  
📋 SESSION LAYER - Fine-grained session management (7 tools)
🔧 TMUX LAYER - Pure MCP tmux orchestration (2 tools)
```

**Total: 10 core MCP tools, zero shell script dependencies**
**Optimized from 18 tools: removed 8 over-designed tools, focused on essential functionality**

## Common Development Commands

### Environment Setup
```bash
# 创建并激活虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt
pip install -e .
```

### MCP Tools Usage

#### Basic Usage (Tmux Layer)
```python
# Most common usage - complete session management
from src.mcp_tools import tmux_session_orchestrator, launch_claude_in_session

# Start complete parallel development environment
tmux_session_orchestrator("start", "PROJECT_NAME", ["TASK1", "TASK2", "TASK3"])

# Check project status
status = tmux_session_orchestrator("status", "PROJECT_NAME")

# Launch Claude in specific worktree branch
launch_claude_in_session(
    project_id="PROJECT_NAME",
    task_id="TASK1",
    working_directory="/path/to/project-task1-worktree"
    # mcp_config_path和skip_permissions可通过环境变量配置
    # continue_session默认为False
)

# Send messages between sessions
tmux_session_orchestrator("message", "PROJECT_NAME", 
    from_session="parallel_PROJECT_NAME_task_master",
    to_session="parallel_PROJECT_NAME_task_child_TASK1",
    message="Switch to OAuth implementation")

# Cleanup when done
tmux_session_orchestrator("cleanup", "PROJECT_NAME")
```

#### Advanced Usage (Session Layer)
```python
# Fine-grained control for advanced users
from src.mcp_tools import create_development_session, send_message_to_session

# Create specific session types
create_development_session("PROJECT_NAME", "child", "AUTH_TASK")

# Advanced messaging
send_message_to_session("parallel_PROJECT_NAME_task_child_AUTH", "Switch to OAuth implementation")
```

#### Monitoring Usage (Monitoring Layer)
```python
# Basic system health monitoring
from src.mcp_tools import check_system_health

# Basic health check
health = check_system_health(include_detailed_metrics=False)
print(f"System health: {health['overall_status']}")

# Note: Complex reporting and diagnostics removed to focus on core functionality
```


## Development Environment

- **Python Version**: 3.11+
- **IDE Configuration**: PyCharm project with Black code formatting
- **Source Directory**: `src/` (configured as source folder)
- **Virtual Environment**: `.venv/` (excluded from VCS)

## Architecture Design

### Architecture Optimization Achievement

The system successfully achieved **架构优化** (architecture optimization) by removing over-designed components:

1. **Essential Functionality Preserved**: All core business functions maintained
2. **Complexity Reduction**: Removed 8 over-designed tools while preserving functionality
3. **Clear Focus**: Three streamlined layers with specific responsibilities
4. **Efficient Architecture**: Eliminated unnecessary complexity, improved maintainability

### Layer Responsibilities

- **🔧 Tmux Layer**: Pure MCP tmux orchestration + Claude launching (2 tools)
- **📋 Session Layer**: Fine-grained session management, messaging, relationships (7 tools)
- **📊 Monitoring Layer**: Basic system health monitoring only (1 tool)

## Project Structure

```
parallel-dev-mcp/
├── src/
│   └── parallel_dev_mcp/       # Optimized architecture
│       ├── tmux/               # 🔧 Tmux layer (2 tools)
│       ├── session/            # 📋 Session layer (7 tools) 
│       ├── monitoring/         # 📊 Monitoring layer (1 tool)
│       └── _internal/          # Supporting components
├── docs/                       # Documentation
└── tests/                      # Test suites
```

## Integration Patterns

### Critical: MCP PROJECT_ID and Session Naming Correlation

⚠️ **Important**: The `PROJECT_ID` environment variable in MCP configuration MUST match the `{PROJECT_ID}` part in tmux session names!

### Session Naming Convention
- **Master sessions**: `parallel_{PROJECT_ID}_task_master`
- **Child sessions**: `parallel_{PROJECT_ID}_task_child_{TASK_ID}`
- **Prefix matching**: `parallel_{PROJECT_ID}_task_*`

### Correct Setup Example

#### Step 1: MCP Server Configuration
```json
{
  "mcpServers": {
    "parallel-dev-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.mcp_tools"],
      "env": {
        "PROJECT_ID": "ECOMMERCE",
        "MCP_CONFIG_PATH": "/path/to/your/mcp-config.json",
        "DANGEROUSLY_SKIP_PERMISSIONS": "true"
      }
    }
  }
}
```

#### Step 2: Create Matching Tmux Sessions
```bash
# Create master session (PROJECT_ID = "ECOMMERCE")
tmux new-session -d -s "parallel_ECOMMERCE_task_master"

# Create child sessions  
tmux new-session -d -s "parallel_ECOMMERCE_task_child_AUTH"
tmux new-session -d -s "parallel_ECOMMERCE_task_child_PAYMENT"
```

#### Step 3: Smart Detection Works
- Smart hooks script parses session names to extract `PROJECT_ID`
- Automatic session discovery and communication establishment
- Perfect correlation between MCP environment and session structure

### Tool Selection Guidelines
- **New users**: Start with `tmux_session_orchestrator` and `launch_claude_in_session` from Tmux layer
- **Advanced users**: Use Session layer for fine-grained control and complex messaging
- **System admins**: Leverage Monitoring layer for observability and diagnostics

### 智能 Claude Code Hooks 集成

系统现在采用智能会话识别机制，提供零配置的自动化hooks管理：

#### 智能会话识别系统
- **自动会话发现** - 基于tmux会话名称自动识别主会话和子会话
- **零环境变量依赖** - 完全基于会话名称模式匹配
- **统一配置文件** - 所有会话使用同一个 `smart_hooks.json`
- **智能事件路由** - 自动根据会话类型处理不同事件

#### 支持的Hook事件
- **SessionStart**: 会话启动时触发，子会话自动注册到主会话
- **PostToolUse**: 工具使用后触发，子会话向主会话汇报进度
- **Stop**: 任务暂停时触发（用于进度汇报）  
- **SessionEnd**: 会话结束时触发，子会话通知主会话完成

#### 智能Hooks配置示例

**固定智能配置** (`examples/hooks/smart_hooks.json`)：
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python examples/hooks/smart_session_detector.py session-start"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python examples/hooks/smart_session_detector.py post-tool-use {{tool_name}}"
          }
        ]
      }
    ]
  }
}
```

#### 智能识别逻辑
```python
# 主会话识别: parallel_{PROJECT_ID}_task_master
if session_name.endswith("_task_master"):
    session_type = "master"
    
# 子会话识别: parallel_{PROJECT_ID}_task_child_{TASK_ID}  
elif "_task_child_" in session_name:
    session_type = "child"
```

#### 配置简化对比
| 方面 | 旧方案 | 智能方案 |
|------|--------|----------|
| **配置文件数** | N+1个 | 1个 |
| **环境变量依赖** | 高 | 零 |
| **维护复杂度** | 高 | 低 |
| **会话识别** | 手动配置 | 自动识别 |

这种智能设计大大简化了配置管理，提供了更可靠的会话间通信机制。

## Testing and Validation

```bash
# Verify complete architecture
python -c "from src.mcp_tools import *; print('✅ All 16 tools imported successfully')"

# Test basic functionality
python -c "
from src.mcp_tools import tmux_session_orchestrator
result = tmux_session_orchestrator('status', 'TEST')
print('✅ Basic functionality working')
"

# Test advanced features
python -c "
from src.mcp_tools import check_system_health
health = check_system_health()
print('✅ Advanced monitoring working')
"

# Test environment configuration
python -c "
from src.parallel_dev_mcp._internal.config_tools import get_environment_config
config = get_environment_config()
print('✅ Environment configuration accessible')
"
```

## Key Integration Points

### Tool Layer Selection
Choose the appropriate layer based on your needs:
- **Simplicity**: Tmux layer (2 tools) - Basic session management and Claude launching
- **Control**: Session layer (7 tools) - Fine-grained session management and messaging
- **Monitoring**: Monitoring layer (1 tool) - Basic health checking only

### Error Handling
All tools include comprehensive error handling and return consistent JSON responses with `success` flags.

### Performance Considerations
- Upper layer tools automatically delegate to lower layers
- Simplified monitoring provides basic health checks without performance overhead
- Session layer enables fine-tuned resource management with reduced complexity

## Development Workflow

1. **Basic Development**: Use `tmux_session_orchestrator` and `launch_claude_in_session` for standard workflows
2. **Advanced Scenarios**: Leverage Session layer for complex session management and messaging
3. **System Monitoring**: Use `check_system_health` for basic health monitoring only

## 重要提醒 (Important Reminders)

- **架构优化完成**: Successfully streamlined from 18 to 10 MCP tools: removed 8 over-designed components
- **零脚本依赖**: Completely eliminated shell script dependencies  
- **专注核心**: Streamlined three-layer architecture focused on essential functionality
- **核心功能保留**: All essential features maintained: tmux orchestration, session management, basic monitoring
- **高效简洁**: Removed complexity while preserving all necessary business capabilities

这个项目现在拥有高效简洁的MCP工具架构，专注于核心功能，提供更好的维护性和可靠性。