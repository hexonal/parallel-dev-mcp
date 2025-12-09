#!/bin/bash
# 通知 Master 任务完成

if [ -n "$PARALLELDEV_MASTER_URL" ] && [ -n "$PARALLELDEV_TASK_ID" ]; then
  curl -s -X POST "$PARALLELDEV_MASTER_URL/api/task-completed" \
    -H "Content-Type: application/json" \
    -d "{\"taskId\": \"$PARALLELDEV_TASK_ID\", \"worker\": \"$PARALLELDEV_WORKER_ID\", \"status\": \"completed\"}" \
    > /dev/null 2>&1 || true
fi
