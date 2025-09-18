# Claude Code Hooks集成

这个目录包含了与Claude Code集成的hooks脚本，支持智能会话检测和自动化Master/Child会话管理。

## 文件说明

### 核心文件

- `web_message_sender.py` - 增强版Web消息发送器，支持智能会话检测
- `stop_hook.sh` - Stop事件hooks脚本
- `session_start_hook.sh` - SessionStart事件hooks脚本

### 配置文件

- `.claude/hooks/stop.md` - Stop hook配置文档
- `.claude/hooks/session_start.md` - SessionStart hook配置文档

## 功能特性

### 智能会话检测

- ✅ 自动检测当前tmux会话名称
- ✅ 智能识别Master/Child会话类型
- ✅ 从Child会话名称提取任务ID
- ✅ 支持PROJECT_PREFIX和WEB_PORT环境变量

### Hook事件处理

- ✅ **Stop Hook**: Child Stop → `/msg/send-child`, Master Stop → `/msg/send`
- ✅ **SessionStart Hook**: Master SessionStart → 写入`session_id.txt`
- ✅ 自动路由到正确的Flask端点
- ✅ 完整的错误处理和状态跟踪

## 配置方法

### 1. 环境变量设置

```bash
# 在 ~/.bashrc 或 ~/.zshrc 中设置
export PROJECT_PREFIX="PARALLEL"  # 项目前缀
export WEB_PORT="5001"           # Flask服务端口
```

### 2. Claude Code Hooks配置

在项目根目录的`.claude/settings.json`中配置：

```json
{
  "hooks": {
    "Stop": [
      {
        "command": "./examples/hooks/stop_hook.sh",
        "description": "处理会话停止事件，支持Master/Child会话区分"
      }
    ],
    "SessionStart": [
      {
        "command": "./examples/hooks/session_start_hook.sh",
        "description": "处理会话开始事件，Master会话写入session_id.txt"
      }
    ]
  }
}
```

### 3. 确保脚本可执行

```bash
chmod +x examples/hooks/*.sh
```

## 使用说明

### 命令行测试

```bash
# 检查会话信息
python examples/hooks/web_message_sender.py session-info

# 健康检查
python examples/hooks/web_message_sender.py health

# 测试Stop hook
python examples/hooks/web_message_sender.py test-hooks Stop

# 测试SessionStart hook
python examples/hooks/web_message_sender.py test-hooks SessionStart

# 发送消息
python examples/hooks/web_message_sender.py send "Hello World"
```

### 手动测试hooks

```bash
# 测试Stop hook
./examples/hooks/stop_hook.sh

# 测试SessionStart hook
export CLAUDE_SESSION_ID="test-session-id-12345"
./examples/hooks/session_start_hook.sh
```

### Hook数据格式测试

```bash
# 模拟Stop事件
echo '{"hook_event_name": "Stop", "session_id": "test-12345"}' | \
  python examples/hooks/web_message_sender.py

# 模拟SessionStart事件
echo '{"hook_event_name": "SessionStart", "session_id": "test-12345"}' | \
  python examples/hooks/web_message_sender.py
```

## 会话类型检测

### Master会话检测

会话名称包含以下特征之一：
- 包含 `_master_`
- 以 `PROJECT_PREFIX` 开头
- 匹配项目前缀模式

例子：`PARALLEL_master_main`, `PARALLEL_dev`, `parallel_main`

### Child会话检测

会话名称包含 `_child_` 关键字：
- 格式：`{PROJECT_PREFIX}_child_{taskId}`
- 例子：`PARALLEL_child_task001`, `parallel_child_auth_feature`

### 任务ID提取

从Child会话名称自动提取任务ID：
- `PARALLEL_child_task001` → `task001`
- `parallel_child_auth_feature` → `auth_feature`

## Flask端点映射

### Child Stop事件 → `/msg/send-child`

```json
{
  "taskId": "task001",
  "sessionName": "PARALLEL_child_task001",
  "status": "success",
  "exitTime": "2024-01-15T10:30:45Z",
  "projectPrefix": "PARALLEL",
  "hookData": {...}
}
```

### Master Stop事件 → `/msg/send`

```json
{
  "sessionId": "session-id-12345",
  "sessionName": "PARALLEL_master_main",
  "status": "stop",
  "timestamp": "2024-01-15T10:30:45Z",
  "projectPrefix": "PARALLEL",
  "hookData": {...}
}
```

### Master SessionStart → session_id.txt写入

仅当`session_id.txt`文件为空或不存在时，写入新的会话ID。

## 错误处理

### 常见问题

1. **会话检测失败**
   - 检查tmux环境变量：`echo $TMUX`
   - 验证会话名称：`tmux display-message -p '#{session_name}'`

2. **端点调用失败**
   - 检查Flask服务状态：`python examples/hooks/web_message_sender.py health`
   - 验证端口配置：`echo $WEB_PORT`

3. **权限错误**
   - 确保脚本可执行：`ls -la examples/hooks/*.sh`
   - 检查文件权限：`chmod +x examples/hooks/*.sh`

### 调试模式

设置详细日志输出：

```bash
export CLAUDE_HOOKS_DEBUG=1
./examples/hooks/stop_hook.sh
```

## 集成检查清单

- [ ] 环境变量已设置（PROJECT_PREFIX, WEB_PORT）
- [ ] Flask服务运行正常（端口5001）
- [ ] Hooks脚本可执行权限
- [ ] Claude Code hooks配置已添加
- [ ] 会话检测正常工作
- [ ] 端点调用测试通过

## 技术架构

```
Claude Code Session
       ↓
   Hook Events (Stop/SessionStart)
       ↓
   Shell Scripts (stop_hook.sh/session_start_hook.sh)
       ↓
   Python Script (web_message_sender.py)
       ↓
   Session Detection + HTTP Request
       ↓
   Flask Endpoints (/msg/send, /msg/send-child)
       ↓
   MCP Resource Updates + Session Management
```

## 扩展功能

可以扩展支持更多Claude Code hook事件：

- `BeforeExecute` - 工具执行前
- `AfterExecute` - 工具执行后
- `OnError` - 错误处理
- `OnFileEdit` - 文件编辑事件

只需在`web_message_sender.py`中添加对应的处理方法即可。