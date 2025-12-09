#!/bin/bash
# 通知 Master 文件变更
FILE_PATH="$1"

if [ -n "$PARALLELDEV_MASTER_URL" ]; then
  curl -s -X POST "$PARALLELDEV_MASTER_URL/api/file-changed" \
    -H "Content-Type: application/json" \
    -d "{\"file\": \"$FILE_PATH\", \"worker\": \"$PARALLELDEV_WORKER_ID\"}" \
    > /dev/null 2>&1 || true
fi
