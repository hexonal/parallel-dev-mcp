#!/bin/bash
# 清理所有 ParallelDev 资源
set -e

echo "🧹 清理 ParallelDev 资源..."

# 1. 杀死所有 tmux 会话
tmux list-sessions 2>/dev/null | grep "parallel-dev" | cut -d: -f1 | while read session; do
  echo "   关闭 tmux 会话: $session"
  tmux kill-session -t "$session" 2>/dev/null || true
done

# 2. 删除所有 worktree
if [ -d ".worktrees" ]; then
  echo "   删除 worktree 目录..."
  git worktree list | grep ".worktrees" | awk '{print $1}' | while read wt; do
    git worktree remove "$wt" --force 2>/dev/null || true
  done
  rm -rf .worktrees
fi

# 3. 清理状态文件
if [ -f ".paralleldev/state.json" ]; then
  echo "   重置状态文件..."
  echo '{"workers":[],"tasks":[],"currentPhase":"idle"}' > .paralleldev/state.json
fi

echo "✅ 清理完成"
