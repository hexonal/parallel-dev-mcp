#!/bin/bash
# 启动单个 Worker
set -e

WORKER_ID="${1:-worker-1}"
WORKTREE_PATH="${2:-.worktrees/$WORKER_ID}"
MASTER_URL="${3:-http://localhost:3001}"

echo "🔧 启动 Worker: $WORKER_ID"
echo "   Worktree: $WORKTREE_PATH"
echo "   Master: $MASTER_URL"

# 创建 tmux 会话
tmux new-session -d -s "parallel-dev-$WORKER_ID" -c "$WORKTREE_PATH"

# 启动 Worker Agent
tmux send-keys -t "parallel-dev-$WORKER_ID" \
  "PARALLELDEV_WORKER_ID=$WORKER_ID PARALLELDEV_MASTER_URL=$MASTER_URL node dist/worker-agent.js" Enter
