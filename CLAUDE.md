# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based parallel development system featuring a **优化的三层MCP工具架构**. All original mcp_server capabilities have been perfectly integrated into mcp_tools with an elegant layered design, now streamlined and focused.

## 🏗️ Architecture Overview

The project now features a clean three-layer architecture:

```
📊 MONITORING LAYER - System monitoring & diagnostics (5 tools)  
📋 SESSION LAYER - Fine-grained session management (11 tools)
🔧 TMUX LAYER - Pure MCP tmux orchestration (2 tools)
```

**Total: 18 MCP tools, zero shell script dependencies**
**Evolved from 16 tools: deleted 5 unnecessary + added 1 core + refined 2 existing**

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

# Launch Claude in specific worktree branch (NEW TOOL!)
launch_claude_in_session(
    project_id="PROJECT_NAME",
    task_id="TASK1", 
    working_directory="/path/to/project-task1-worktree",
    mcp_config_path="/path/to/mcp.json"
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

# Advanced messaging with priorities
send_message_to_session("parallel_PROJECT_NAME_task_child_AUTH", "Urgent: Switch to OAuth2.0",
                       message_type="command", priority="urgent")
```

#### Monitoring Usage (Monitoring Layer)
```python
# System health and diagnostics
from src.mcp_tools import check_system_health, generate_status_report

# Comprehensive health check
health = check_system_health(include_detailed_metrics=True)
print(f"System health: {health['overall_status']}")

# Generate detailed status report
report = generate_status_report(time_period="24h", format="summary")
```


## Development Environment

- **Python Version**: 3.11+
- **IDE Configuration**: PyCharm project with Black code formatting
- **Source Directory**: `src/` (configured as source folder)
- **Virtual Environment**: `.venv/` (excluded from VCS)

## Architecture Design

### Perfect Fusion Achievement

The system successfully achieved **完美融合** (perfect fusion) of mcp_server capabilities into mcp_tools:

1. **Zero Capability Loss**: All original server functions preserved
2. **Elegant Refactoring**: From 1505-line monolith to modular components  
3. **Clear Separation**: Three focused layers with specific responsibilities
4. **Streamlined Architecture**: Eliminated unnecessary complexity while preserving core functionality

### Layer Responsibilities

- **🔧 Tmux Layer**: Pure MCP tmux orchestration + Claude launching, replaces all shell scripts
- **📋 Session Layer**: Fine-grained session management, messaging, relationships
- **📊 Monitoring Layer**: System health, diagnostics, performance monitoring

## Project Structure

```
parallel-dev-mcp/
├── src/
│   ├── mcp_tools/               # Streamlined fusion architecture
│   │   ├── tmux/               # 🔧 Tmux layer (2 tools)
│   │   ├── session/            # 📋 Session layer (11 tools) 
│   │   └── monitoring/         # 📊 Monitoring layer (5 tools)
│   └── mcp_server/             # Supporting components (called by tools)
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
        "PYTHONPATH": "/path/to/parallel-dev-mcp"
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

# Test intelligent hooks configuration
python tools/config_generator.py --project-id TEST --tasks AUTH API UI --output-dir ./test_configs
echo "✅ Smart hooks configuration generated"
```

## Key Integration Points

### Tool Layer Selection
Choose the appropriate layer based on your needs:
- **Simplicity**: Tmux layer (1 tool)
- **Control**: Session layer (11 tools)
- **Monitoring**: Monitoring layer (6 tools)  
- **Orchestration**: Orchestrator layer (3 tools)

### Error Handling
All tools include comprehensive error handling and return consistent JSON responses with `success` flags.

### Performance Considerations
- Upper layer tools automatically delegate to lower layers
- Monitoring layer provides performance metrics and bottleneck identification
- Session layer enables fine-tuned resource management

## Development Workflow

1. **Basic Development**: Use `tmux_session_orchestrator` and `launch_claude_in_session` for standard workflows
2. **Advanced Scenarios**: Leverage Session layer for complex session management  
3. **System Monitoring**: Use Monitoring layer for health checks and diagnostics

## 重要提醒 (Important Reminders)

- **架构优化完成**: Successfully evolved from 16 to 18 MCP tools: -5 unnecessary +1 core +2 refined
- **零脚本依赖**: Completely eliminated shell script dependencies  
- **分层清晰**: Clean three-layer architecture with focused responsibilities
- **新增核心功能**: Added Claude launching tool with worktree support
- **向上兼容**: Upper layers automatically utilize lower layer capabilities

这个项目现在拥有优化的分层MCP工具架构，专注于核心功能，能够满足从基础用户到系统管理的所有需求。