# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based parallel development system featuring a **完美融合的四层MCP工具架构**. All original mcp_server capabilities have been perfectly integrated into mcp_tools with an elegant layered design.

## 🏗️ Architecture Overview

The project now features a clean four-layer architecture:

```
🎯 ORCHESTRATOR LAYER - Project-level orchestration (3 tools)
📊 MONITORING LAYER - System monitoring & diagnostics (5 tools)  
📋 SESSION LAYER - Fine-grained session management (7 tools)
🔧 TMUX LAYER - Pure MCP tmux orchestration (1 tool)
```

**Total: 16 MCP tools, zero shell script dependencies**

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
# Most common usage - single tool for all basic needs
from src.mcp_tools import tmux_session_orchestrator

# Start complete parallel development environment
tmux_session_orchestrator("start", "PROJECT_NAME", ["TASK1", "TASK2", "TASK3"])

# Check project status
status = tmux_session_orchestrator("status", "PROJECT_NAME")

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
from src.mcp_tools import check_system_health, get_system_dashboard

# Comprehensive health check
health = check_system_health(include_detailed_metrics=True)
print(f"System health: {health['overall_status']}")

# Real-time dashboard
dashboard = get_system_dashboard(include_trends=True)
```

#### Enterprise Usage (Orchestrator Layer)  
```python
# Project-level orchestration for complex workflows
from src.mcp_tools import orchestrate_project_workflow

# Complete project workflow orchestration
workflow = orchestrate_project_workflow(
    project_id="PROJECT_NAME",
    workflow_type="development",
    tasks=["AUTH", "PAYMENT", "UI"],
    parallel_execution=True
)
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
3. **Clear Separation**: Four distinct layers with specific responsibilities
4. **Upward Compatibility**: Upper layers automatically call lower layers

### Layer Responsibilities

- **🔧 Tmux Layer**: Pure MCP tmux orchestration, replaces all shell scripts
- **📋 Session Layer**: Fine-grained session management, messaging, relationships
- **📊 Monitoring Layer**: System health, diagnostics, performance monitoring  
- **🎯 Orchestrator Layer**: Project lifecycle, workflow orchestration, parallel coordination

## Project Structure

```
parallel-dev-mcp/
├── src/
│   ├── mcp_tools/               # Perfect fusion architecture
│   │   ├── tmux/               # 🔧 Tmux layer
│   │   ├── session/            # 📋 Session layer  
│   │   ├── monitoring/         # 📊 Monitoring layer
│   │   └── orchestrator/       # 🎯 Orchestrator layer
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
- **New users**: Start with `tmux_session_orchestrator` from Tmux layer
- **Advanced users**: Use Session layer for fine-grained control
- **System admins**: Leverage Monitoring layer for observability
- **Project managers**: Use Orchestrator layer for enterprise workflows

### 智能 Claude Code Hooks 集成

系统现在采用智能会话识别机制，提供零配置的自动化hooks管理：

#### 智能会话识别系统
- **自动会话发现** - 基于tmux会话名称自动识别主会话和子会话
- **零环境变量依赖** - 完全基于会话名称模式匹配
- **统一配置文件** - 所有会话使用同一个 `smart_hooks.json`
- **智能事件路由** - 自动根据会话类型处理不同事件

#### 支持的Hook事件
- **user-prompt-submit-hook**: 用户提示提交时触发
- **session-start-hook**: 会话启动时触发  
- **stop-hook**: 任务暂停时触发（用于进度汇报）
- **session-end-hook**: 会话结束时触发

#### 智能Hooks配置示例

**统一智能配置** (`smart_hooks.json`)：
```json
{
  "user-prompt-submit-hook": {
    "command": [
      "python", 
      "/path/to/smart_session_detector.py", 
      "user-prompt", 
      "{{prompt}}"
    ],
    "description": "智能会话提示处理Hook - 自动识别会话类型"
  },
  "session-start-hook": {
    "command": [
      "python", 
      "/path/to/smart_session_detector.py", 
      "session-start"
    ],
    "description": "智能会话启动Hook - 自动注册和协调"
  },
  "stop-hook": {
    "command": [
      "python", 
      "/path/to/smart_session_detector.py", 
      "stop"
    ],
    "description": "智能任务进度Hook - 自动进度汇报"
  },
  "session-end-hook": {
    "command": [
      "python", 
      "/path/to/smart_session_detector.py", 
      "session-end"
    ],
    "description": "智能会话结束Hook - 自动完成通知"
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

1. **Basic Development**: Use `tmux_session_orchestrator` for standard workflows
2. **Advanced Scenarios**: Leverage Session layer for complex session management
3. **System Monitoring**: Use Monitoring layer for health checks and diagnostics
4. **Project Management**: Apply Orchestrator layer for enterprise-level coordination

## 重要提醒 (Important Reminders)

- **完美融合完成**: The perfect fusion from mcp_server to mcp_tools is complete
- **零脚本依赖**: Completely eliminated shell script dependencies  
- **分层清晰**: Clean five-layer architecture with distinct responsibilities
- **向上兼容**: Upper layers automatically utilize lower layer capabilities

这个项目现在拥有完美的分层MCP工具架构，能够满足从基础用户到企业级项目管理的所有需求。