#!/bin/bash
# 启动子会话脚本模板

PROJECT_ROOT="/Users/flink/parallel-dev-mcp"
PROJECT_ID="DEMO_TEST"
MASTER_SESSION="master_project_DEMO_TEST"

# 使用方法: scripts/setup_claude_code.sh TASK_ID
if [ -z "$1" ]; then
    echo "用法: $0 TASK_ID"
    echo "示例: $0 AUTH"
    exit 1
fi

TASK_ID="$1"
SESSION_NAME="child_${PROJECT_ID}_task_${TASK_ID}"

echo "启动子会话: $SESSION_NAME (任务: $TASK_ID)"

tmux new-session -s "$SESSION_NAME" -d \
  -e "PROJECT_ID=$PROJECT_ID" \
  -e "TASK_ID=$TASK_ID" \
  -e "MASTER_SESSION_ID=$MASTER_SESSION" \
  -e "SESSION_ROLE=child" \
  -e "HOOKS_CONFIG_PATH=$PROJECT_ROOT/config/hooks/${SESSION_NAME}_hooks.json" \
  "claude"

echo "子会话已启动，使用以下命令连接:"
echo "tmux attach-session -t $SESSION_NAME"
