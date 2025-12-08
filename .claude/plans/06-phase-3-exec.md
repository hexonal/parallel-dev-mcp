# Phase 3: Layer 3 执行层（Tmux + Worktree）

> 本文件包含 ParallelDev 执行层实施细节

---

## TODO 完成规范

> **🔴 重要**：每个 TODO 小点完成后，执行以下流程：
> 1. 使用 task agent 进行自测验证
> 2. 询问用户是否提交推送代码
> 3. 如用户同意，执行 `git add -A && git commit && git push`

---

## 目标

实现 Git Worktree 管理和 Tmux 会话控制，满足需求：
- R3.1: Worker 运行在独立 worktree 中
- R3.2: 每个 Worker 有独立 Tmux 会话
- R3.3: Worker 运行 Claude Code 执行任务

---

## TODO 3.1: 实现 WorktreeManager.ts

**文件**: `src/parallel/git/WorktreeManager.ts`

**核心方法**：

```typescript
export interface WorktreeInfo {
  path: string;
  branch: string;
  taskId: string;
  createdAt: string;
}

export class WorktreeManager {
  private projectRoot: string;
  private worktreeDir: string;

  constructor(projectRoot: string, worktreeDir: string = '.worktrees');

  // 创建 worktree
  async create(taskId: string, baseBranch: string = 'main'): Promise<WorktreeInfo>;

  // 删除 worktree
  async remove(taskId: string): Promise<void>;

  // 列出所有 worktree
  list(): WorktreeInfo[];

  // 检查 worktree 是否存在
  exists(taskId: string): boolean;

  // 清理所有 worktree
  async cleanup(): Promise<void>;
}
```

**Git 命令映射**：

| 操作 | 命令 |
|------|------|
| 创建 | `git worktree add .worktrees/task-{id} -b task/{id} main` |
| 删除 | `git worktree remove .worktrees/task-{id} --force` |
| 列出 | `git worktree list --porcelain` |

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 3.2: 实现 ConflictDetector.ts

**文件**: `src/parallel/git/ConflictDetector.ts`

**核心方法**：

```typescript
export class ConflictDetector {
  // 检测 worktree 中的冲突
  async detectConflicts(worktreePath: string): Promise<ConflictInfo[]>;

  // 检查是否有冲突
  async hasConflicts(worktreePath: string): Promise<boolean>;

  // 获取冲突级别
  getConflictLevel(file: string): ConflictLevel;

  // 获取冲突标记内容
  private async getConflictMarkers(worktreePath: string, file: string): Promise<string[]>;
}
```

**冲突级别分类**：

| 级别 | 文件类型 | 解决方式 |
|------|----------|----------|
| Level 1 | package-lock.json, yarn.lock, .prettierrc | 自动解决 |
| Level 2 | .ts, .js, .json, .md | AI 辅助 |
| Level 3 | 其他 | 人工介入 |

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 3.3: 实现 TmuxController.ts

**文件**: `src/parallel/tmux/TmuxController.ts`

**核心方法**：

```typescript
export class TmuxController {
  private sessionPrefix: string;

  constructor(sessionPrefix: string = 'parallel-dev');

  // 创建新的 tmux 会话
  async createSession(sessionId: string, workingDir: string): Promise<string>;

  // 杀死 tmux 会话
  async killSession(sessionName: string): Promise<void>;

  // 向会话发送命令
  async sendCommand(sessionName: string, command: string): Promise<void>;

  // 捕获会话输出
  async captureOutput(sessionName: string, lines: number = 1000): Promise<string>;

  // 列出所有会话
  listSessions(): string[];

  // 检查会话是否存在
  sessionExists(sessionName: string): boolean;
}
```

**Tmux 命令映射**：

| 操作 | 命令 |
|------|------|
| 创建会话 | `tmux new-session -d -s {name} -c {dir}` |
| 杀死会话 | `tmux kill-session -t {name}` |
| 发送命令 | `tmux send-keys -t {name} '{cmd}' Enter` |
| 捕获输出 | `tmux capture-pane -t {name} -p -S -{lines}` |
| 列出会话 | `tmux list-sessions -F "#{session_name}"` |

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 3.4: 实现 SessionMonitor.ts

**文件**: `src/parallel/tmux/SessionMonitor.ts`

**核心方法**：

```typescript
export class SessionMonitor extends EventEmitter {
  private tmux: TmuxController;
  private sessions: Map<string, NodeJS.Timeout> = new Map();
  private checkInterval: number;

  constructor(tmux: TmuxController, checkInterval: number = 1000);

  // 开始监控会话
  startMonitoring(sessionName: string): void;

  // 停止监控会话
  stopMonitoring(sessionName: string): void;

  // 停止所有监控
  stopAll(): void;
}
```

**事件类型**：

| 事件 | 数据 | 触发时机 |
|------|------|----------|
| `output` | `{ sessionName, content }` | 检测到新输出 |
| `error` | `{ sessionName, error }` | 会话异常 |
| `completed` | `{ sessionName }` | 检测到完成标记 |

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 3.5: 实现 TaskExecutor.ts

**文件**: `src/parallel/worker/TaskExecutor.ts`

**核心方法**：

```typescript
export class TaskExecutor {
  private tmux: TmuxController;
  private monitor: SessionMonitor;
  private tmuxSession: string;

  constructor(tmux: TmuxController, monitor: SessionMonitor, tmuxSession: string);

  // 执行任务
  async execute(task: Task, worktreePath: string): Promise<TaskResult>;

  // 构建任务 Prompt
  private buildTaskPrompt(task: Task): string;

  // 等待任务完成
  private async waitForCompletion(): Promise<TaskResult>;

  // 解析 stream-json 输出
  private parseStreamJson(output: string): StreamEvent[];
}
```

**Claude Headless 命令**：

```bash
claude -p "{prompt}" \
  --output-format stream-json \
  --permission-mode acceptEdits \
  --allowedTools Read,Edit,Write,Bash,Grep,Glob
```

**任务 Prompt 模板**：

```
你是 ParallelDev Worker，正在执行任务。

## 任务信息
- ID: {task.id}
- 标题: {task.title}
- 描述: {task.description}

## 执行要求
1. 完成任务描述中的所有需求
2. 遵循项目代码规范
3. 编写必要的测试
4. 任务完成后输出 "TASK_COMPLETED"

开始执行任务。
```

**完成后**：task agent 自测 → 询问是否提交推送

---

## Phase 3 验收标准

- [ ] `WorktreeManager.create()` 正确创建 worktree
- [ ] `WorktreeManager.remove()` 正确删除 worktree
- [ ] `TmuxController.createSession()` 正确创建会话
- [ ] `TmuxController.sendCommand()` 正确发送命令
- [ ] `TmuxController.captureOutput()` 正确捕获输出
- [ ] `TaskExecutor.execute()` 能执行 Claude Headless
- [ ] 所有单元测试通过

---

## 需求满足追溯

| 需求 | 实现文件 | 验证方法 |
|------|----------|----------|
| R3.1 | `WorktreeManager.ts` | `create()` 创建独立 worktree |
| R3.2 | `TmuxController.ts` | `createSession()` 创建会话 |
| R3.3 | `TaskExecutor.ts` | `execute()` 运行 Claude |

---

## 快速导航

- ← [Phase 2: Layer 1 任务管理](05-phase-2-task.md)
- → [Phase 4-8: 通信/质量/编排/通知/集成](07-phase-4-8.md)
- [返回索引](00-index.md)
