# MCP Session Coordinator 使用指南

## 系统概述

Session Coordinator MCP是一个专为Claude Code设计的会话管理和通信系统，支持多会话并行开发工作流。

## 核心功能

### 6个MCP工具

| 工具名称 | 用途 | 调用者 |
|---------|------|--------|
| `register_session_relationship` | 注册主子会话关系 | 主会话 |
| `report_session_status` | 上报工作状态和进度 | 子会话 |
| `get_child_sessions` | 获取所有子会话状态 | 主会话 |
| `query_session_status` | 查询特定会话状态 | 任意会话 |
| `send_message_to_session` | 发送指令或消息 | 主会话 |
| `get_session_messages` | 获取未读消息 | 子会话 |

## 使用方式

### 方式1：通过Claude Code Hooks自动调用

这是推荐的生产使用方式，通过hooks实现自动化。

#### 步骤1：生成hooks配置

```bash
# 生成主会话hooks配置
python3 -m src.hooks.hooks_manager generate master master_project_MYPROJECT --project-id MYPROJECT

# 生成子会话hooks配置  
python3 -m src.hooks.hooks_manager generate child child_MYPROJECT_task_AUTH --project-id MYPROJECT --master-session-id master_project_MYPROJECT --task-id AUTH
```

#### 步骤2：启动带hooks的会话

```bash
# 创建主会话
python3 -m src.hooks.hooks_manager create-session master master_project_MYPROJECT --project-id MYPROJECT

# 创建子会话
python3 -m src.hooks.hooks_manager create-session child child_MYPROJECT_task_AUTH --project-id MYPROJECT --master-session-id master_project_MYPROJECT --task-id AUTH
```

### 方式2：手动MCP工具调用

用于测试、调试或特殊场景。

#### 启动MCP服务器

```bash
cd /path/to/parallel-dev-mcp
python3 -m src.mcp_server.server
```

#### 在Claude Code中调用MCP工具

```python
# 1. 注册会话关系 (主会话执行)
register_session_relationship(
    parent_session="master_project_MYPROJECT",
    child_session="child_MYPROJECT_task_AUTH", 
    task_id="AUTH",
    project_id="MYPROJECT"
)

# 2. 子会话上报状态
report_session_status(
    session_name="child_MYPROJECT_task_AUTH",
    status="WORKING",
    progress=50,
    details="实现用户认证逻辑"
)

# 3. 主会话查询子会话
get_child_sessions(parent_session="master_project_MYPROJECT")

# 4. 发送指令给子会话
send_message_to_session(
    from_session="master_project_MYPROJECT",
    to_session="child_MYPROJECT_task_AUTH",
    message="请确认代码已提交并通过测试",
    message_type="INSTRUCTION"
)

# 5. 子会话获取消息
get_session_messages(session_name="child_MYPROJECT_task_AUTH")
```

## 会话命名约定

### 主会话命名
格式：`master_project_{PROJECT_ID}`
示例：`master_project_ECOMMERCE`

### 子会话命名  
格式：`child_{PROJECT_ID}_task_{TASK_ID}`
示例：`child_ECOMMERCE_task_AUTH`

## 典型工作流

### 1. 项目启动阶段

```bash
# 主会话：创建项目管理会话
tmux new-session -s "master_project_ECOMMERCE" -d \
  -e "PROJECT_ID=ECOMMERCE" \
  -e "SESSION_ROLE=master" \
  "claude"
```

### 2. 任务分配阶段

```bash
# 创建认证任务子会话
tmux new-session -s "child_ECOMMERCE_task_AUTH" -d \
  -e "PROJECT_ID=ECOMMERCE" \
  -e "TASK_ID=AUTH" \
  -e "MASTER_SESSION_ID=master_project_ECOMMERCE" \
  -e "SESSION_ROLE=child" \
  "claude"

# 创建支付任务子会话
tmux new-session -s "child_ECOMMERCE_task_PAYMENT" -d \
  -e "PROJECT_ID=ECOMMERCE" \
  -e "TASK_ID=PAYMENT" \
  -e "MASTER_SESSION_ID=master_project_ECOMMERCE" \
  -e "SESSION_ROLE=child" \
  "claude"
```

### 3. 开发过程中

子会话通过hooks自动：
- 启动时注册到主会话
- 工具调用后上报进度 
- 定期检查来自主会话的消息
- 任务完成时通知主会话

主会话可以：
- 定期监控所有子会话状态
- 向特定子会话发送指令
- 处理子会话完成通知

### 4. 项目合并阶段

主会话检测到所有子任务完成后：
- 收集所有代码变更
- 执行集成测试
- 创建合并提交
- 通知项目完成

## 状态和消息类型

### 会话状态枚举
- `UNKNOWN`: 未知状态
- `STARTING`: 正在启动
- `STARTED`: 已启动
- `WORKING`: 工作中
- `COMPLETED`: 已完成
- `BLOCKED`: 被阻塞
- `ERROR`: 出错
- `TERMINATED`: 已终止

### 消息类型
- `INSTRUCTION`: 指令消息
- `QUERY`: 查询消息  
- `STATUS_REQUEST`: 状态请求

## 配置和环境变量

### MCP服务器配置

在Claude Code配置中添加：

```json
{
  "mcpServers": {
    "session-coordinator": {
      "command": ["python3", "-m", "src.mcp_server.server"],
      "args": [],
      "cwd": "/path/to/parallel-dev-mcp"
    }
  }
}
```

### 环境变量

| 变量名 | 用途 | 示例值 |
|--------|------|--------|
| `PROJECT_ID` | 项目标识符 | `ECOMMERCE` |
| `TASK_ID` | 任务标识符 | `AUTH` |
| `SESSION_ROLE` | 会话角色 | `master`/`child` |
| `MASTER_SESSION_ID` | 主会话ID | `master_project_ECOMMERCE` |
| `WORKTREE_PATH` | 工作树路径 | `../worktrees/task-AUTH` |

## 故障排除

### 常见问题

1. **会话名称格式错误**
   - 确保遵循命名约定
   - 使用hooks_manager生成配置

2. **MCP服务器连接失败**
   - 检查服务器是否启动
   - 验证配置路径正确

3. **消息传递失败**
   - 确认会话关系已注册
   - 检查会话名称是否存在

### 调试命令

```bash
# 列出活跃会话
python3 -m src.hooks.hooks_manager list-sessions

# 查看系统状态
python3 -c "
from src.mcp_server.session_coordinator import SessionCoordinatorMCP
coordinator = SessionCoordinatorMCP('debug')
print(coordinator.query_session_status())
"

# 运行系统验证
python3 scripts/validate_mcp_system.py
```

## 高级用法

### 自定义hooks处理器

可以在hooks配置中定义自定义处理逻辑：

```json
{
  "response_handlers": {
    "custom_handler": {
      "description": "自定义处理逻辑",
      "actions": [
        {"type": "custom_action", "handler": "my_handler"}
      ]
    }
  }
}
```

### 批量操作

MCP服务器支持高性能批量操作：

```python
# 批量注册多个子会话
for task_id in ["AUTH", "PAYMENT", "SHIPPING"]:
    register_session_relationship(
        parent_session="master_project_ECOMMERCE",
        child_session=f"child_ECOMMERCE_task_{task_id}",
        task_id=task_id,
        project_id="ECOMMERCE"
    )
```

### 性能优化

- 使用批量操作减少MCP调用次数
- 合理设置hooks触发间隔
- 定期清理过期会话数据

## 集成示例

完整的集成示例请参考：
- [演示脚本](../scripts/demo_workflow.sh)
- [单元测试](../tests/test_session_coordinator.py) 
- [Hooks模板](../src/hooks/)