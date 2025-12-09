---
name: parallel-executor
description: 并行任务执行能力 - 管理 Worker、Worktree、任务调度。启用 ParallelDev 并行开发系统。
triggers:
  - parallel
  - 并行
  - worktree
  - worker
  - 任务执行
  - tmux
  - ParallelDev
---

# Parallel Executor Skill

启用 ParallelDev 并行执行能力，包括 Git Worktree 管理、Tmux 会话控制、Claude Headless 执行。

## 快速参考

**详细规范**: 见 [REFERENCE.md](REFERENCE.md)

---

## 核心能力

| 能力 | 描述 |
|------|------|
| Git Worktree | 为每个任务创建独立工作目录 |
| Tmux 会话 | 管理并行执行的终端会话 |
| Claude Headless | 在隔离环境中执行 Claude Code |
| 任务调度 | 智能分配和监控任务 |

---

## Git Worktree 管理

### 创建 Worktree
```bash
# 创建任务专属 worktree
git worktree add .worktrees/task-{id} -b task/{id}

# 验证创建
ls .worktrees/task-{id}
```

### 删除 Worktree
```bash
# 删除 worktree
git worktree remove .worktrees/task-{id}

# 强制删除（有未提交更改时）
git worktree remove --force .worktrees/task-{id}

# 清理
git worktree prune
```

### 列出 Worktree
```bash
git worktree list
```

### Worktree 目录结构
```
project/
├── .worktrees/
│   ├── task-001/           # 任务 1 工作目录
│   ├── task-002/           # 任务 2 工作目录
│   └── task-003/           # 任务 3 工作目录
├── src/                    # 主分支源码
└── .git/
```

---

## Tmux 会话管理

### 创建会话
```bash
# 创建后台会话
tmux new-session -d -s parallel-dev-{id}

# 创建并设置工作目录
tmux new-session -d -s parallel-dev-{id} -c /path/to/worktree
```

### 发送命令
```bash
# 发送命令到会话
tmux send-keys -t parallel-dev-{id} 'command' Enter

# 发送多行命令
tmux send-keys -t parallel-dev-{id} 'cd /path && npm install' Enter
```

### 捕获输出
```bash
# 捕获当前 pane 输出
tmux capture-pane -t parallel-dev-{id} -p

# 捕获指定行数
tmux capture-pane -t parallel-dev-{id} -p -S -100
```

### 会话管理
```bash
# 列出会话
tmux list-sessions

# 附加到会话
tmux attach -t parallel-dev-{id}

# 杀死会话
tmux kill-session -t parallel-dev-{id}

# 杀死所有 parallel-dev 会话
tmux kill-session -t parallel-dev-*
```

---

## Claude Headless 执行

### 启动命令
```bash
# 在 worktree 中执行
cd .worktrees/task-{id}
claude -p "task prompt" --output-format stream-json
```

### 输出格式
```json
{"type": "message", "content": "..."}
{"type": "tool_use", "name": "Read", "input": {...}}
{"type": "tool_result", "output": "..."}
{"type": "result", "status": "success"}
```

### 状态检测
- `result.status === "success"` → 任务完成
- `result.status === "error"` → 任务失败
- 无输出超时 → 任务挂起

---

## 任务生命周期

```
┌─────────────┐
│   PENDING   │  ← 初始状态
└──────┬──────┘
       │ 分配 Worker
       ▼
┌─────────────┐
│   ASSIGNED  │  ← 已分配
└──────┬──────┘
       │ 创建 Worktree + Tmux
       ▼
┌─────────────┐
│   RUNNING   │  ← 执行中
└──────┬──────┘
       │
   ┌───┴───┐
   ▼       ▼
┌──────┐ ┌──────┐
│ DONE │ │FAILED│
└──────┘ └──────┘
```

### 状态转换触发
| 状态变化 | 触发条件 |
|----------|----------|
| PENDING → ASSIGNED | Worker 可用且任务被分配 |
| ASSIGNED → RUNNING | Worktree 创建成功 |
| RUNNING → DONE | Claude 返回 success |
| RUNNING → FAILED | Claude 返回 error 或超时 |

---

## 使用示例

### TypeScript 调用
```typescript
// 创建 Worker
const worktree = await worktreeManager.create('task-001');
const tmux = await tmuxController.createSession('parallel-dev-001', worktree.path);

// 执行任务
const result = await taskExecutor.execute({
    taskId: 'task-001',
    prompt: 'Implement user authentication',
    worktreePath: worktree.path,
    tmuxSession: tmux.sessionName
});

// 清理
await tmuxController.killSession('parallel-dev-001');
await worktreeManager.remove('task-001');
```

---

## MCP 工具集成

| 工具 | 用途 |
|------|------|
| sequential-thinking | 任务分解、依赖分析 |
| context7 | Git/Tmux 官方文档查询 |
| deepwiki | Git Worktree/Tmux 技术文档 |
| git-config | Git 用户信息获取 |
| mcp-datetime | 时间戳生成 |

---

## 检查清单

### 执行前
- [ ] 主分支干净（无未提交更改）
- [ ] 任务定义明确
- [ ] 依赖任务已完成

### 执行中
- [ ] Worktree 创建成功
- [ ] Tmux 会话运行正常
- [ ] 定期捕获输出检查状态

### 执行后
- [ ] 代码提交到任务分支
- [ ] Worktree 清理
- [ ] Tmux 会话清理
- [ ] 冲突检测（如有）

---

## 参考文档

- **[REFERENCE.md](REFERENCE.md)** - 详细 API、状态机、错误处理
