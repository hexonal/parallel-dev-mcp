# Tmux会话编排器 - 纯MCP解决方案

## 🎯 概述

这是一个**纯MCP工具**，完全替代了原有的7个Shell脚本，同时保持了tmux的所有优势。

### ✅ 替代的脚本功能
- `setup_claude_code.sh` → `tmux_session_orchestrator("init")`
- `start_master_*.sh` → `tmux_session_orchestrator("start")` (master会话)
- `start_child_*.sh` → `tmux_session_orchestrator("start")` (child会话)
- `status_*.sh` → `tmux_session_orchestrator("status")`  
- `cleanup_*.sh` → `tmux_session_orchestrator("cleanup")`
- 会话间通信 → `tmux_session_orchestrator("message")`
- 会话管理 → `tmux_session_orchestrator("attach", "list")`

## 🚀 快速开始

### 1. 初始化项目
```python
result = tmux_session_orchestrator(
    "init", 
    "ECOMMERCE_PROJECT", 
    tasks=["AUTH", "PAYMENT", "UI"]
)
```

### 2. 启动所有会话
```python
result = tmux_session_orchestrator(
    "start", 
    "ECOMMERCE_PROJECT", 
    tasks=["AUTH", "PAYMENT", "UI"]
)
```

### 3. 检查项目状态
```python
status = tmux_session_orchestrator("status", "ECOMMERCE_PROJECT")
print(f"健康会话: {status['healthy_sessions']}/{status['total_sessions']}")
```

### 4. 会话间通信
```python
# 主会话向AUTH子会话发送指令
result = tmux_session_orchestrator(
    "message", "ECOMMERCE_PROJECT",
    from_session="master_project_ECOMMERCE_PROJECT",
    to_session="child_ECOMMERCE_PROJECT_task_AUTH", 
    message="请报告当前开发进度"
)
```

### 5. 获取连接说明
```python
# 获取主会话连接命令
attach_info = tmux_session_orchestrator("attach", "ECOMMERCE_PROJECT", session_type="master")
print(attach_info["command"])  # tmux attach-session -t master_project_ECOMMERCE_PROJECT

# 获取所有子会话列表
sessions = tmux_session_orchestrator("attach", "ECOMMERCE_PROJECT", session_type="list")
```

### 6. 清理项目环境
```python
result = tmux_session_orchestrator("cleanup", "ECOMMERCE_PROJECT")
```

## 🛠️ 完整API参考

### tmux_session_orchestrator(action, project_id, **kwargs)

#### 参数
- `action` (str): 操作类型
- `project_id` (str): 项目ID
- `tasks` (List[str], 可选): 任务列表
- `from_session` (str, 可选): 源会话名 (用于message)
- `to_session` (str, 可选): 目标会话名 (用于message) 
- `message` (str, 可选): 消息内容
- `session_type` (str, 可选): 会话类型 (用于attach)

#### 支持的action

| Action | 描述 | 必需参数 | 替代的脚本 |
|--------|------|----------|------------|
| `init` | 初始化项目配置 | `project_id`, `tasks` | setup_claude_code.sh |
| `start` | 启动所有会话 | `project_id`, `tasks` | start_master_*.sh, start_child_*.sh |
| `status` | 获取项目状态 | `project_id` | status_*.sh |
| `message` | 会话间发送消息 | `project_id`, `from_session`, `to_session`, `message` | MCP工具间通信 |
| `attach` | 获取会话连接说明 | `project_id`, `session_type` | 手动tmux命令 |
| `list` | 列出所有会话 | `project_id` | tmux list-sessions |
| `cleanup` | 清理项目环境 | `project_id` | cleanup_*.sh |

## 🏗️ 架构设计

### 会话层次结构
```
MCP工具 (在协调者会话中运行)
    ↓ 创建和管理
master_project_{PROJECT_ID}          (父会话)
├── child_{PROJECT_ID}_task_AUTH      (子会话1)  
├── child_{PROJECT_ID}_task_PAYMENT   (子会话2)
└── child_{PROJECT_ID}_task_UI        (子会话3)
```

### 通信机制
1. **MCP服务器通信** - 通过现有的MCP服务器API
2. **文件系统通信** - 通过JSON消息文件作为备用
3. **环境变量传递** - tmux会话启动时传递项目信息

### 项目文件结构
```
projects/{PROJECT_ID}/
├── config/
│   ├── claude-config.json       # Claude配置
│   ├── master_hooks.json        # 主会话hooks
│   ├── child_AUTH_hooks.json    # AUTH任务hooks  
│   └── child_PAYMENT_hooks.json # PAYMENT任务hooks
├── messages/                    # 会话间消息
│   ├── messages_master_project_{PROJECT_ID}.json
│   └── messages_child_{PROJECT_ID}_task_AUTH.json
└── project_metadata.json       # 项目元数据
```

## 🧪 测试和验证

### 运行完整测试
```bash
cd src/mcp_tools/
python test_tmux_orchestrator.py full
```

### 运行单功能测试
```bash
python test_tmux_orchestrator.py unit
```

### 交互式演示
```bash
python test_tmux_orchestrator.py demo
```

## 🎯 核心优势

### ✅ 解决的问题
1. **复杂性降低**: 7个脚本 → 1个MCP工具
2. **用户体验**: 统一的MCP接口，无需记忆多个命令
3. **维护简化**: 单一代码库，统一的错误处理
4. **权限安全**: MCP工具权限，无需系统级权限

### ✅ 保持的优势  
1. **tmux性能**: 原生进程，零容器开销
2. **会话持久性**: 完美的会话保持和恢复
3. **终端体验**: 原生终端交互，直接attach
4. **调试便利**: 直接查看会话状态和日志

### ✅ 新增的能力
1. **智能通信**: 会话间消息传递和状态同步
2. **健康监控**: 实时会话健康检查
3. **自动清理**: 完整的环境清理和恢复
4. **错误处理**: 完善的异常处理和回滚机制

## 🔧 与现有系统集成

### MCP服务器集成
这个工具可以与您现有的MCP服务器无缝集成:

```python  
# 在现有MCP服务器中添加
from src.mcp_tools import tmux_session_orchestrator

# 现有MCP工具可以调用tmux编排器
@mcp_tool("parallel_dev_setup")
def parallel_dev_setup(project_id: str, tasks: List[str]):
    # 初始化tmux环境
    init_result = tmux_session_orchestrator("init", project_id, tasks)
    if "error" in init_result:
        return init_result
    
    # 启动会话
    start_result = tmux_session_orchestrator("start", project_id, tasks)
    return start_result
```

### 现有MCP工具兼容性
- ✅ 保持所有现有MCP工具的功能
- ✅ 增强会话管理和通信能力  
- ✅ 提供统一的会话生命周期管理
- ✅ 支持现有的状态同步和消息传递

## 🚀 立即开始

1. **测试基本功能**:
   ```bash
   python test_tmux_orchestrator.py full
   ```

2. **创建您的第一个项目**:
   ```python
   from src.mcp_tools import tmux_session_orchestrator
   
   # 初始化
   tmux_session_orchestrator("init", "MY_PROJECT", ["BACKEND", "FRONTEND"])
   
   # 启动
   tmux_session_orchestrator("start", "MY_PROJECT", ["BACKEND", "FRONTEND"])
   ```

3. **连接到会话**:
   ```bash
   # 连接到主会话
   tmux attach-session -t master_project_MY_PROJECT
   
   # 连接到具体任务会话
   tmux attach-session -t child_MY_PROJECT_task_BACKEND
   ```

现在您拥有了一个完全基于MCP、零Shell脚本的并行开发系统！🎉