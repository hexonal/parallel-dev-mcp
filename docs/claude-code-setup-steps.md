# Claude Code MCP配置详细步骤

## 🎯 配置目标

将Session Coordinator MCP服务器集成到Claude Code中，让你在Claude Code中可以使用6个会话管理工具。

## 🚀 方法一：一键自动配置（推荐）

```bash
# 进入项目目录
cd /Users/flink/parallel-dev-mcp

# 运行自动配置脚本（将YOUR_PROJECT替换为你的项目名）
bash scripts/setup_claude_code.sh --project-id YOUR_PROJECT

# 例如：
bash scripts/setup_claude_code.sh --project-id ECOMMERCE
```

这个脚本会自动：
- ✅ 配置MCP服务器到Claude Code
- ✅ 生成项目专用的hooks配置
- ✅ 创建启动和管理脚本
- ✅ 运行系统验证

## 🛠️ 方法二：手动配置步骤

如果你想了解配置细节或需要自定义配置，可以手动配置。

### 步骤1：创建Claude Code配置文件

Claude Code的配置文件位置：`~/.claude/config.json`

```bash
# 创建Claude配置目录
mkdir -p ~/.claude

# 创建或编辑配置文件
nano ~/.claude/config.json
```

### 步骤2：添加MCP服务器配置

在 `~/.claude/config.json` 中添加以下内容：

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

**重要说明：**
- `cwd`: 必须是你实际的项目路径
- `PYTHONPATH`: 确保Python能找到我们的模块

### 步骤3：验证MCP服务器配置

```bash
# 测试MCP服务器是否能正常启动
cd /Users/flink/parallel-dev-mcp
python3 -m src.mcp_server.server

# 如果看到以下输出，说明配置正确：
# Session Coordinator MCP服务器
# ==================================================
# 服务器名称: session-coordinator
# 可用MCP工具: ...
```

### 步骤4：重启Claude Code

```bash
# 如果Claude Code正在运行，需要重启让配置生效
# 退出Claude Code，然后重新启动
claude
```

## 🔧 方法三：项目特定配置

如果你只想在特定项目中使用MCP服务器：

### 1. 在项目根目录创建`.claude`文件夹

```bash
# 进入你的项目目录
cd /path/to/your/project

# 创建Claude配置目录
mkdir -p .claude
```

### 2. 创建项目配置文件

在 `.claude/config.json` 中添加：

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

### 3. 在项目目录启动Claude Code

```bash
# 在包含.claude/config.json的目录中启动
claude
```

## 🧪 验证配置是否成功

### 1. 启动Claude Code并检查MCP工具

启动Claude Code后，你应该能看到6个可用的MCP工具：

- `register_session_relationship`
- `report_session_status`
- `get_child_sessions`
- `query_session_status`
- `send_message_to_session`
- `get_session_messages`

### 2. 测试MCP工具

在Claude Code中尝试调用一个MCP工具：

```python
# 测试查询系统状态
query_session_status()
```

你应该会看到类似这样的返回：
```json
{
  "total_sessions": 0,
  "sessions": {}
}
```

### 3. 运行完整验证

```bash
# 运行系统验证脚本
python3 /Users/flink/parallel-dev-mcp/scripts/validate_mcp_system.py

# 应该显示：17/17 测试通过 (100%成功率)
```

## 🎮 开始使用

### 启动并行开发会话

```bash
# 1. 创建主会话（项目协调）
tmux new-session -s "master_project_MYPROJECT" -d \
  -e "PROJECT_ID=MYPROJECT" \
  -e "SESSION_ROLE=master" \
  "claude"

# 2. 创建子会话（具体任务）
tmux new-session -s "child_MYPROJECT_task_AUTH" -d \
  -e "PROJECT_ID=MYPROJECT" \
  -e "TASK_ID=AUTH" \
  -e "MASTER_SESSION_ID=master_project_MYPROJECT" \
  -e "SESSION_ROLE=child" \
  "claude"

# 3. 进入主会话
tmux attach-session -t "master_project_MYPROJECT"
```

### 在Claude Code中使用MCP工具

**在主会话中：**
```python
# 注册子会话关系
register_session_relationship(
    parent_session="master_project_MYPROJECT",
    child_session="child_MYPROJECT_task_AUTH",
    task_id="AUTH",
    project_id="MYPROJECT"
)

# 查询所有子会话状态
get_child_sessions(parent_session="master_project_MYPROJECT")

# 发送指令给子会话
send_message_to_session(
    from_session="master_project_MYPROJECT",
    to_session="child_MYPROJECT_task_AUTH",
    message="请开始代码实现",
    message_type="INSTRUCTION"
)
```

**在子会话中：**
```python
# 上报工作状态
report_session_status(
    session_name="child_MYPROJECT_task_AUTH",
    status="WORKING",
    progress=50,
    details="正在实现用户认证逻辑"
)

# 获取来自主会话的消息
get_session_messages(session_name="child_MYPROJECT_task_AUTH")
```

## 🚨 常见问题排查

### 问题1：MCP服务器启动失败

**症状：** Claude Code显示MCP连接错误

**解决方案：**
```bash
# 检查Python路径
which python3

# 测试手动启动
cd /Users/flink/parallel-dev-mcp
python3 -m src.mcp_server.server

# 检查依赖是否正确安装
python3 -c "from src.mcp_server.session_coordinator import SessionCoordinatorMCP"
```

### 问题2：找不到MCP工具

**症状：** Claude Code中没有显示6个MCP工具

**解决方案：**
```bash
# 检查配置文件路径
ls -la ~/.claude/config.json

# 检查配置文件内容
cat ~/.claude/config.json

# 重启Claude Code
```

### 问题3：路径配置错误

**症状：** MCP服务器启动时报路径错误

**解决方案：**
```bash
# 检查实际项目路径
pwd
# 确保config.json中的cwd路径正确

# 更新配置文件中的路径
nano ~/.claude/config.json
```

## 🔄 配置文件模板

### 全局配置模板（~/.claude/config.json）

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
  },
  "settings": {
    "theme": "dark",
    "autoSave": true
  }
}
```

### 项目配置模板（.claude/config.json）

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
  },
  "projectSettings": {
    "defaultProjectId": "MYPROJECT",
    "sessionManagement": {
      "enabled": true,
      "masterSessionPrefix": "master_project_",
      "childSessionPrefix": "child_"
    }
  }
}
```

## 🎯 配置完成检查清单

- [ ] `~/.claude/config.json` 文件已创建
- [ ] MCP服务器配置已添加
- [ ] 项目路径正确设置
- [ ] MCP服务器可以手动启动
- [ ] Claude Code重启后可以看到MCP工具
- [ ] MCP工具可以正常调用
- [ ] 系统验证脚本通过

完成以上步骤后，你就可以在Claude Code中使用强大的并行会话管理功能了！🚀