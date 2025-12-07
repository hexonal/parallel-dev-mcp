#!/bin/bash
# 启动 Master Orchestrator
set -e

PROJECT_ROOT="${1:-.}"
WORKERS="${2:-3}"
TASKS_FILE="${3:-.taskmaster/tasks/tasks.json}"

echo "🚀 启动 ParallelDev Master..."
echo "   项目目录: $PROJECT_ROOT"
echo "   Worker 数量: $WORKERS"
echo "   任务文件: $TASKS_FILE"

cd "$PROJECT_ROOT"
node dist/cli-parallel.js run \
  --tasks "$TASKS_FILE" \
  --workers "$WORKERS"
