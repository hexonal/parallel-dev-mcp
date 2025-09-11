#!/bin/bash
# 清理项目会话: DEMO_TEST

PROJECT_ID="DEMO_TEST"

echo "清理 DEMO_TEST 项目的所有会话..."

# 终止所有相关tmux会话
tmux list-sessions 2>/dev/null | grep "DEMO_TEST" | cut -d: -f1 | while read session; do
    echo "终止会话: $session"
    tmux kill-session -t "$session" 2>/dev/null || true
done

echo "清理完成"
