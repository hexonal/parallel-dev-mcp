# Stop Hook Configuration

执行方式：当Claude Code会话停止时触发

## Hook脚本

```bash
#!/bin/bash

# Stop Hook - 会话停止时调用web_message_sender.py
# 支持Master和Child会话的不同处理逻辑

# 设置环境变量
export PROJECT_PREFIX="${PROJECT_PREFIX:-PARALLEL}"
export WEB_PORT="${WEB_PORT:-5001}"

# 获取当前目录的Python脚本路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WEB_MESSAGE_SENDER="${PROJECT_ROOT}/examples/hooks/web_message_sender.py"

# 检查脚本是否存在
if [ ! -f "$WEB_MESSAGE_SENDER" ]; then
    echo "错误: web_message_sender.py 不存在: $WEB_MESSAGE_SENDER"
    exit 1
fi

# 构建hook数据
HOOK_DATA=$(cat <<EOF
{
    "hook_event_name": "Stop",
    "session_id": "${CLAUDE_SESSION_ID:-}",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)",
    "project_root": "${PROJECT_ROOT}",
    "working_directory": "$(pwd)",
    "environment": {
        "PROJECT_PREFIX": "${PROJECT_PREFIX}",
        "WEB_PORT": "${WEB_PORT}",
        "TMUX": "${TMUX:-}",
        "USER": "${USER:-}",
        "PWD": "${PWD}"
    }
}
EOF
)

# 发送hook数据到web_message_sender.py
echo "$HOOK_DATA" | python3 "$WEB_MESSAGE_SENDER"

# 记录执行结果
RESULT=$?
if [ $RESULT -eq 0 ]; then
    echo "Stop hook 执行成功"
else
    echo "Stop hook 执行失败，退出码: $RESULT"
fi

exit $RESULT
```