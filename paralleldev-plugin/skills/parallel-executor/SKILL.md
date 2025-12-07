---
name: parallel-executor
description: 并行任务执行能力 - 管理 Worker、Worktree、任务调度
triggers:
  - parallel
  - 并行
  - worktree
  - worker
  - 任务执行
---

# Parallel Executor Skill

启用 ParallelDev 并行执行能力。

## 能力范围

### Git Worktree 管理
- 创建独立 worktree: `git worktree add .worktrees/task-{id} -b task/{id}`
- 删除 worktree: `git worktree remove .worktrees/task-{id}`
- 列出 worktree: `git worktree list`

### Tmux 会话管理
- 创建会话: `tmux new-session -d -s parallel-dev-{id}`
- 发送命令: `tmux send-keys -t parallel-dev-{id} 'command' Enter`
- 捕获输出: `tmux capture-pane -t parallel-dev-{id} -p`

### Claude Headless 执行
- 启动命令: `claude -p "task prompt" --output-format stream-json`
- 解析 stream-json 输出
- 检测任务完成状态

## 使用示例

```typescript
// 创建 Worker
const worktree = await worktreeManager.create('task-1');
const tmux = await tmuxController.createSession('parallel-dev-1', worktree.path);
await taskExecutor.execute(task, worktree.path);
```
