#!/bin/bash
# 启动主会话: master_project_DEMO_TEST

PROJECT_ROOT="/Users/flink/parallel-dev-mcp"
SESSION_NAME="master_project_DEMO_TEST"

echo "启动主会话: $SESSION_NAME"

tmux new-session -s "$SESSION_NAME" -d \
  -e "PROJECT_ID=DEMO_TEST" \
  -e "SESSION_ROLE=master" \
  -e "HOOKS_CONFIG_PATH=$PROJECT_ROOT/config/hooks/${SESSION_NAME}_hooks.json" \
  "claude"

echo "主会话已启动，使用以下命令连接:"
echo "tmux attach-session -t $SESSION_NAME"
