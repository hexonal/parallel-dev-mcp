# Parallel Executor 详细参考

## 目录
- [API 说明](#api-说明)
- [状态机详细](#状态机详细)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)

---

## API 说明

### WorktreeManager

```typescript
interface WorktreeManager {
    // 创建 worktree
    create(taskId: string): Promise<Worktree>;

    // 删除 worktree
    remove(taskId: string): Promise<void>;

    // 强制删除（有未提交更改时）
    forceRemove(taskId: string): Promise<void>;

    // 列出所有 worktree
    list(): Promise<Worktree[]>;

    // 检查 worktree 是否存在
    exists(taskId: string): Promise<boolean>;

    // 清理孤立 worktree
    prune(): Promise<void>;
}

interface Worktree {
    taskId: string;
    path: string;
    branch: string;
    createdAt: Date;
}
```

### TmuxController

```typescript
interface TmuxController {
    // 创建会话
    createSession(sessionName: string, workingDir: string): Promise<TmuxSession>;

    // 发送命令
    sendKeys(sessionName: string, command: string): Promise<void>;

    // 捕获输出
    captureOutput(sessionName: string, lines?: number): Promise<string>;

    // 杀死会话
    killSession(sessionName: string): Promise<void>;

    // 列出会话
    listSessions(): Promise<TmuxSession[]>;

    // 检查会话是否存在
    sessionExists(sessionName: string): Promise<boolean>;
}

interface TmuxSession {
    name: string;
    workingDir: string;
    createdAt: Date;
    pid: number;
}
```

### TaskExecutor

```typescript
interface TaskExecutor {
    // 执行任务
    execute(config: ExecuteConfig): Promise<ExecuteResult>;

    // 取消执行
    cancel(taskId: string): Promise<void>;

    // 获取执行状态
    getStatus(taskId: string): Promise<TaskStatus>;
}

interface ExecuteConfig {
    taskId: string;
    prompt: string;
    worktreePath: string;
    tmuxSession: string;
    timeout?: number;
}

interface ExecuteResult {
    taskId: string;
    status: 'success' | 'error' | 'timeout';
    output?: string;
    error?: string;
    duration: number;
}
```

---

## 状态机详细

### 任务状态

```typescript
enum TaskStatus {
    PENDING = 'pending',      // 等待分配
    ASSIGNED = 'assigned',    // 已分配 Worker
    RUNNING = 'running',      // 执行中
    DONE = 'done',            // 完成
    FAILED = 'failed',        // 失败
    CANCELLED = 'cancelled'   // 已取消
}
```

### 状态转换规则

```
PENDING ─────┬───────────> ASSIGNED
             │                │
             │                ▼
             │            RUNNING
             │                │
             │     ┌──────┬───┴───┬──────┐
             │     ▼      ▼       ▼      ▼
             │   DONE   FAILED  TIMEOUT CANCELLED
             │
             └───────────────────────────> CANCELLED
```

### 转换条件

| 转换 | 条件 | 动作 |
|------|------|------|
| PENDING → ASSIGNED | Worker 可用 | 创建 Worktree |
| ASSIGNED → RUNNING | Worktree 就绪 | 启动 Claude |
| RUNNING → DONE | Claude 成功 | 提交代码 |
| RUNNING → FAILED | Claude 失败 | 记录错误 |
| RUNNING → TIMEOUT | 超时 | 杀死进程 |
| * → CANCELLED | 用户取消 | 清理资源 |

---

## 错误处理

### 错误类型

```typescript
class WorktreeError extends Error {
    constructor(
        message: string,
        public taskId: string,
        public cause?: Error
    ) {
        super(message);
        this.name = 'WorktreeError';
    }
}

class TmuxError extends Error {
    constructor(
        message: string,
        public sessionName: string,
        public cause?: Error
    ) {
        super(message);
        this.name = 'TmuxError';
    }
}

class ExecutionError extends Error {
    constructor(
        message: string,
        public taskId: string,
        public status: TaskStatus,
        public cause?: Error
    ) {
        super(message);
        this.name = 'ExecutionError';
    }
}
```

### 错误恢复策略

| 错误类型 | 恢复策略 |
|----------|----------|
| Worktree 创建失败 | 清理后重试 |
| Tmux 会话失败 | 杀死后重建 |
| Claude 超时 | 记录日志，标记失败 |
| 冲突检测 | 触发 conflict-resolution |

### 清理流程

```typescript
async function cleanup(taskId: string) {
    // 1. 杀死 Tmux 会话
    try {
        await tmuxController.killSession(`parallel-dev-${taskId}`);
    } catch (e) {
        console.warn(`Failed to kill tmux: ${e.message}`);
    }

    // 2. 删除 Worktree
    try {
        await worktreeManager.forceRemove(taskId);
    } catch (e) {
        console.warn(`Failed to remove worktree: ${e.message}`);
    }

    // 3. 清理孤立资源
    await worktreeManager.prune();
}
```

---

## 最佳实践

### 并发限制

```typescript
const MAX_CONCURRENT_TASKS = 3;

// 检查是否可以启动新任务
async function canStartNewTask(): Promise<boolean> {
    const running = await getRunningTasks();
    return running.length < MAX_CONCURRENT_TASKS;
}
```

### 资源监控

```typescript
// 定期检查资源状态
setInterval(async () => {
    const sessions = await tmuxController.listSessions();
    const worktrees = await worktreeManager.list();

    // 检查孤立会话
    for (const session of sessions) {
        if (!hasActiveTask(session.name)) {
            await tmuxController.killSession(session.name);
        }
    }

    // 检查孤立 worktree
    for (const worktree of worktrees) {
        if (!hasActiveTask(worktree.taskId)) {
            await worktreeManager.remove(worktree.taskId);
        }
    }
}, 60000); // 每分钟检查
```

### 日志记录

```typescript
// 任务开始
console.log(`📦 Task ${taskId} started`);
console.log(`   Worktree: ${worktree.path}`);
console.log(`   Session: ${tmux.name}`);

// 任务完成
console.log(`✅ Task ${taskId} completed in ${duration}ms`);

// 任务失败
console.error(`❌ Task ${taskId} failed: ${error.message}`);
```

### 超时设置

```typescript
const DEFAULT_TIMEOUT = 10 * 60 * 1000; // 10 分钟

async function executeWithTimeout(config: ExecuteConfig) {
    const timeout = config.timeout || DEFAULT_TIMEOUT;

    return Promise.race([
        taskExecutor.execute(config),
        new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), timeout)
        )
    ]);
}
```
