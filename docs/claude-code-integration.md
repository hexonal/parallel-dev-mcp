# Claude Code 集成配置指南

## 概述

本指南详细说明如何将Session Coordinator MCP服务器集成到Claude Code中，实现多会话并行开发功能。

## 第一步：配置MCP服务器

### 1.1 创建MCP服务器配置

在Claude Code配置文件中添加Session Coordinator MCP服务器：

**位置**: `~/.claude/config.json` 或项目的 `.claude/config.json`

```json
{
  "mcpServers": {
    "session-coordinator": {
      "command": ["python3", "-m", "src.mcp_server.server"],
      "args": [],
      "cwd": "/Users/flink/parallel-dev-mcp",
      "timeout": 30000,
      "env": {
        "PYTHONPATH": "/Users/flink/parallel-dev-mcp"
      }
    }
  }
}
```

### 1.2 验证MCP服务器配置

```bash
# 测试MCP服务器是否正常启动
cd /Users/flink/parallel-dev-mcp
python3 -m src.mcp_server.server --test-mode

# 验证所有工具可用
python3 -c "
from src.mcp_server.session_coordinator import SessionCoordinatorMCP
coordinator = SessionCoordinatorMCP('test')
print('MCP服务器已就绪')
"
```

## 第二步：配置Claude Hooks

### 2.1 生成Hooks配置文件

使用hooks管理器生成配置：

```bash
# 生成主会话hooks配置
python3 -m src.hooks.hooks_manager generate master master_project_MYPROJECT \
  --project-id MYPROJECT \
  --output config/hooks/master_hooks.json

# 生成子会话hooks配置
python3 -m src.hooks.hooks_manager generate child child_MYPROJECT_task_AUTH \
  --project-id MYPROJECT \
  --master-session-id master_project_MYPROJECT \
  --task-id AUTH \
  --output config/hooks/child_hooks.json
```

### 2.2 安装Hooks到Claude Code

有两种方式安装hooks配置：

#### 方式1：全局hooks配置（适用于项目级别）

```bash
# 将hooks配置复制到Claude配置目录
cp config/hooks/master_hooks.json ~/.claude/hooks.json

# 或者为特定项目创建hooks
mkdir -p .claude
cp config/hooks/master_hooks.json .claude/hooks.json
```

#### 方式2：会话特定hooks（推荐用于多会话场景）

```bash
# 创建会话特定的配置目录
mkdir -p ~/.claude/sessions/master_project_MYPROJECT
cp config/hooks/master_hooks.json ~/.claude/sessions/master_project_MYPROJECT/hooks.json

mkdir -p ~/.claude/sessions/child_MYPROJECT_task_AUTH  
cp config/hooks/child_hooks.json ~/.claude/sessions/child_MYPROJECT_task_AUTH/hooks.json
```

## 第三步：启动会话

### 3.1 启动主会话

```bash
# 方式1：直接启动Claude Code主会话
tmux new-session -s "master_project_MYPROJECT" -d \
  -e "PROJECT_ID=MYPROJECT" \
  -e "SESSION_ROLE=master" \
  -e "HOOKS_CONFIG_PATH=$PWD/config/hooks/master_hooks.json" \
  "claude"

# 方式2：使用hooks管理器自动创建
python3 -m src.hooks.hooks_manager create-session master master_project_MYPROJECT \
  --project-id MYPROJECT
```

### 3.2 启动子会话

```bash
# 方式1：手动启动子会话
tmux new-session -s "child_MYPROJECT_task_AUTH" -d \
  -e "PROJECT_ID=MYPROJECT" \
  -e "TASK_ID=AUTH" \
  -e "MASTER_SESSION_ID=master_project_MYPROJECT" \
  -e "SESSION_ROLE=child" \
  -e "HOOKS_CONFIG_PATH=$PWD/config/hooks/child_hooks.json" \
  "claude"

# 方式2：使用hooks管理器自动创建
python3 -m src.hooks.hooks_manager create-session child child_MYPROJECT_task_AUTH \
  --project-id MYPROJECT \
  --master-session-id master_project_MYPROJECT \
  --task-id AUTH
```

## 第四步：Claude Code中的使用

### 4.1 可用的MCP工具

在Claude Code会话中，以下MCP工具将自动可用：

1. **register_session_relationship** - 注册主子会话关系
2. **report_session_status** - 上报工作状态
3. **get_child_sessions** - 获取子会话列表  
4. **query_session_status** - 查询会话状态
5. **send_message_to_session** - 发送消息
6. **get_session_messages** - 获取消息

### 4.2 在Claude Code中手动调用MCP工具

```python
# 在主会话中注册子会话关系
register_session_relationship(
    parent_session="master_project_MYPROJECT",
    child_session="child_MYPROJECT_task_AUTH",
    task_id="AUTH", 
    project_id="MYPROJECT"
)

# 在子会话中上报状态
report_session_status(
    session_name="child_MYPROJECT_task_AUTH",
    status="WORKING",
    progress=50,
    details="正在实现JWT认证逻辑"
)

# 在主会话中查询所有子会话
get_child_sessions(parent_session="master_project_MYPROJECT")

# 在主会话中发送指令
send_message_to_session(
    from_session="master_project_MYPROJECT",
    to_session="child_MYPROJECT_task_AUTH", 
    message="请确认代码已提交并通过测试",
    message_type="INSTRUCTION"
)

# 在子会话中检查消息
get_session_messages(session_name="child_MYPROJECT_task_AUTH")
```

## 第五步：自动化Hooks工作流

### 5.1 Hooks自动触发场景

当配置了hooks后，以下操作会自动触发MCP工具调用：

**子会话hooks自动执行：**
- **会话启动时**: 自动注册到主会话
- **工具调用后**: 自动上报进度状态  
- **任务完成时**: 自动通知主会话完成
- **定期检查**: 每30秒检查来自主会话的消息

**主会话hooks自动执行：**
- **会话启动时**: 初始化MCP连接
- **定期监控**: 每5分钟查询所有子会话状态
- **子会话完成时**: 处理完成通知
- **手动触发**: 发送指令到子会话

### 5.2 环境变量配置

确保以下环境变量正确设置：

```bash
# 必需的环境变量
export PROJECT_ID="MYPROJECT"           # 项目标识符
export SESSION_ROLE="master"            # 或 "child"
export TASK_ID="AUTH"                   # 子会话必需
export MASTER_SESSION_ID="master_project_MYPROJECT"  # 子会话必需

# 可选的环境变量
export WORKTREE_PATH="../worktrees/task-AUTH"  # Git worktree路径
export HOOKS_CONFIG_PATH="./config/hooks/child_hooks.json"  # Hooks配置路径
```

## 第六步：实际使用示例

### 6.1 完整的项目开发工作流

```bash
# 1. 启动项目主会话
tmux new-session -s "master_project_ECOMMERCE" -d \
  -e "PROJECT_ID=ECOMMERCE" \
  -e "SESSION_ROLE=master" \
  "claude"

# 2. 启动认证模块子会话
tmux new-session -s "child_ECOMMERCE_task_AUTH" -d \
  -e "PROJECT_ID=ECOMMERCE" \
  -e "TASK_ID=AUTH" \
  -e "MASTER_SESSION_ID=master_project_ECOMMERCE" \
  -e "SESSION_ROLE=child" \
  "claude"

# 3. 启动支付模块子会话
tmux new-session -s "child_ECOMMERCE_task_PAYMENT" -d \
  -e "PROJECT_ID=ECOMMERCE" \
  -e "TASK_ID=PAYMENT" \
  -e "MASTER_SESSION_ID=master_project_ECOMMERCE" \
  -e "SESSION_ROLE=child" \
  "claude"

# 4. 查看所有会话
tmux list-sessions

# 5. 进入主会话监控进度
tmux attach-session -t "master_project_ECOMMERCE"
```

### 6.2 在Claude Code中的操作

**在主会话中：**
```
# Claude Code会自动执行hooks，但你也可以手动查询：
查询所有子会话状态：get_child_sessions(parent_session="master_project_ECOMMERCE")

# 发送指令给特定子会话：
send_message_to_session(
    from_session="master_project_ECOMMERCE",
    to_session="child_ECOMMERCE_task_AUTH",
    message="请开始代码review准备",
    message_type="INSTRUCTION"
)
```

**在子会话中：**
```
# Claude Code会自动上报状态，但你也可以手动上报：
report_session_status(
    session_name="child_ECOMMERCE_task_AUTH",
    status="WORKING", 
    progress=75,
    details="JWT认证逻辑实现完成，正在编写测试"
)

# 检查来自主会话的消息：
get_session_messages(session_name="child_ECOMMERCE_task_AUTH")
```

## 第七步：故障排除

### 7.1 常见问题

**问题1: MCP服务器连接失败**
```bash
# 检查服务器是否能正常启动
cd /Users/flink/parallel-dev-mcp
python3 -m src.mcp_server.server

# 检查Python路径
python3 -c "import sys; print(sys.path)"
```

**问题2: Hooks不执行**
```bash
# 检查hooks配置文件是否存在
ls -la ~/.claude/hooks.json
ls -la .claude/hooks.json

# 检查环境变量
echo $SESSION_ROLE
echo $PROJECT_ID
```

**问题3: 会话名称格式错误**
```bash
# 验证会话名称格式
python3 -c "
from src.mcp_server.session_utils import validate_session_name
print(validate_session_name('master_project_MYPROJECT'))
print(validate_session_name('child_MYPROJECT_task_AUTH'))
"
```

### 7.2 调试工具

```bash
# 查看活跃会话
python3 -m src.hooks.hooks_manager list-sessions

# 运行完整验证
python3 scripts/validate_mcp_system.py

# 查看MCP工具演示
python3 docs/mcp-tools-demo.py

# 清理旧的hooks配置
python3 -m src.hooks.hooks_manager cleanup
```

## 第八步：高级配置

### 8.1 自定义Hooks行为

修改hooks配置文件中的触发条件：

```json
{
  "hooks": {
    "after-tool-call": {
      "description": "工具调用后自动上报",
      "conditions": ["tool_success", "significant_progress"],
      "commands": [...]
    }
  }
}
```

### 8.2 性能优化

```json
{
  "hooks": {
    "periodic-check": {
      "description": "定期检查消息",
      "interval_seconds": 60,  // 可调整检查频率
      "commands": [...]
    }
  }
}
```

### 8.3 集成FastMCP 2.0

```bash
# 如果使用FastMCP 2.0，添加到配置中
export FASTMCP_INTEGRATION=true
export FASTMCP_SERVER_URL="http://localhost:8000"
```

## 第九步：完整的开发工作流示例

### 9.1 项目初始化

```bash
# 1. 克隆或创建项目
git clone https://github.com/yourproject/ecommerce.git
cd ecommerce

# 2. 配置MCP系统
git clone https://github.com/flink/parallel-dev-mcp.git
cd parallel-dev-mcp

# 3. 生成项目专用的hooks配置
python3 -m src.hooks.hooks_manager generate master master_project_ECOMMERCE --project-id ECOMMERCE
python3 -m src.hooks.hooks_manager generate child child_ECOMMERCE_task_AUTH --project-id ECOMMERCE --master-session-id master_project_ECOMMERCE --task-id AUTH
```

### 9.2 开发阶段

```bash
# 1. 启动主会话（项目协调）
python3 -m src.hooks.hooks_manager create-session master master_project_ECOMMERCE --project-id ECOMMERCE

# 2. 根据需要启动子会话（具体任务）
python3 -m src.hooks.hooks_manager create-session child child_ECOMMERCE_task_AUTH --project-id ECOMMERCE --master-session-id master_project_ECOMMERCE --task-id AUTH
python3 -m src.hooks.hooks_manager create-session child child_ECOMMERCE_task_PAYMENT --project-id ECOMMERCE --master-session-id master_project_ECOMMERCE --task-id PAYMENT

# 3. 开发过程中，Claude Code会自动：
#    - 子会话上报开发进度
#    - 主会话监控整体进度  
#    - 会话间自动消息传递
#    - 任务完成时自动通知
```

### 9.3 项目完成

```bash
# 1. 主会话会自动检测所有子任务完成
# 2. 可以手动查询最终状态
python3 -c "
from src.mcp_server.session_coordinator import SessionCoordinatorMCP
coordinator = SessionCoordinatorMCP('final-check')
result = coordinator.get_child_sessions('master_project_ECOMMERCE')
print(result)
"

# 3. 清理会话
tmux kill-session -t master_project_ECOMMERCE
tmux kill-session -t child_ECOMMERCE_task_AUTH
tmux kill-session -t child_ECOMMERCE_task_PAYMENT
```

## 总结

通过以上配置，您的Claude Code将具备：

✅ **自动会话管理** - 通过hooks自动处理会话生命周期  
✅ **实时进度同步** - 子会话自动上报状态到主会话  
✅ **双向消息传递** - 主子会话间可以发送指令和查询  
✅ **并行开发支持** - 多个子会话可以同时进行不同任务  
✅ **完整工作流集成** - 从项目启动到完成的全流程支持  

现在您可以开始使用这个强大的并行开发系统了！🚀