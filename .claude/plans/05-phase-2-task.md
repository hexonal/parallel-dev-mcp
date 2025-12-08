# Phase 2: Layer 1 任务管理（爆改代码）

> 本文件包含 ParallelDev 任务管理层实施细节

---

## TODO 完成规范

> **🔴 重要**：每个 TODO 小点完成后，执行以下流程：
> 1. 使用 task agent 进行自测验证
> 2. 询问用户是否提交推送代码
> 3. 如用户同意，执行 `git add -A && git commit && git push`

---

## 目标

实现任务依赖图和调度器，满足需求：
- R1.1: 集成 task-master 精细化任务管理
- R1.2: 任务依赖 DAG
- R1.3: 并行度识别
- R1.4: 动态任务分配
- R1.5: 优先级支持

---

## TODO 2.1: 爆改/保留 TaskDAG.ts

**文件**: `src/parallel/task/TaskDAG.ts`

**步骤**：
```bash
# 2.1.1 对比 task-master 版本
diff claude-task-master/src/???/dag.ts src/parallel/task/TaskDAG.ts || true

# 2.1.2 选择更优实现或合并
# 2.1.3 编写单元测试
# 2.1.4 运行测试验证
vitest run src/parallel/task/TaskDAG.test.ts
```

**核心方法**：

```typescript
export class TaskDAG {
  private tasks: Map<string, Task> = new Map();
  private completedTasks: Set<string> = new Set();
  private failedTasks: Set<string> = new Set();

  // 添加任务
  addTask(task: Task): void;
  addTasks(tasks: Task[]): void;

  // 获取可执行任务（依赖已满足且状态为 pending）
  getReadyTasks(): Task[];

  // 标记任务状态
  markCompleted(taskId: string): void;
  markFailed(taskId: string, error: string): void;
  markRunning(taskId: string, workerId: string): void;

  // 循环依赖检测
  hasCycle(): boolean;

  // 拓扑排序
  topologicalSort(): string[];

  // 统计信息
  getStats(): { total, pending, running, completed, failed };
}
```

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 2.2: 爆改 TaskScheduler.ts

**文件**: `src/parallel/task/TaskScheduler.ts`

**步骤**：
```bash
# 2.2.1 移除 LOAD_BALANCED 策略
# 2.2.2 保留 PRIORITY_FIRST + DEPENDENCY_FIRST
# 2.2.3 编写单元测试
vitest run src/parallel/task/TaskScheduler.test.ts
```

**核心方法**：

```typescript
export class TaskScheduler {
  private strategy: SchedulingStrategy;
  private dag: TaskDAG;

  constructor(dag: TaskDAG, strategy: SchedulingStrategy = 'priority_first');

  // 设置/获取策略
  setStrategy(strategy: SchedulingStrategy): void;
  getStrategy(): SchedulingStrategy;

  // 调度任务（返回排序后的可执行任务列表）
  schedule(): Task[];

  // 按优先级排序（数字越小优先级越高）
  private sortByPriority(tasks: Task[]): Task[];

  // 按解锁依赖数量排序（能解锁更多任务的优先）
  private sortByDependencyUnlock(tasks: Task[]): Task[];

  // 获取下一个要执行的任务
  getNextTask(): Task | undefined;

  // 获取可并行执行的任务组
  getParallelTasks(maxWorkers: number): Task[];
}
```

**调度策略**：

1. **priority_first**：按优先级排序，数字越小优先级越高
2. **dependency_first**：能解锁更多后续任务的优先

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 2.3: 爆改 TaskManager.ts（原 TaskMasterAdapter）

**文件**: `src/parallel/task/TaskManager.ts`

**步骤**：
```bash
# 2.3.1 重命名为 TaskManager
# 2.3.2 使用 Zod 验证
# 2.3.3 编写单元测试
vitest run src/parallel/task/TaskManager.test.ts
```

**核心方法**：

```typescript
export class TaskManager {
  private projectRoot: string;
  private tasksFilePath: string;
  private dag: TaskDAG;
  private scheduler: TaskScheduler;

  constructor(projectRoot: string, config: ParallelDevConfig);

  // 检查任务文件是否存在
  tasksFileExists(): boolean;

  // 加载任务文件（Zod 验证 + 循环依赖检测）
  async loadTasks(): Promise<Task[]>;

  // 保存任务状态
  async saveTasks(): Promise<void>;

  // 验证单个任务
  validateTask(task: Partial<Task>): { valid: boolean; errors: string[] };

  // 获取 DAG 和调度器
  getDAG(): TaskDAG;
  getScheduler(): TaskScheduler;

  // 获取可执行任务
  getReadyTasks(): Task[];

  // 调度下一批任务
  scheduleNextBatch(maxWorkers: number): Task[];

  // 标记任务状态
  markTaskStarted(taskId: string, workerId: string): void;
  markTaskCompleted(taskId: string): void;
  markTaskFailed(taskId: string, error: string): void;

  // 检查是否所有任务已完成
  isAllCompleted(): boolean;

  // 获取统计信息
  getStats(): { total, pending, running, completed, failed };
}
```

**完成后**：task agent 自测 → 询问是否提交推送

---

## Phase 2 验收标准

- [ ] `TaskDAG.getReadyTasks()` 正确返回可执行任务
- [ ] `TaskDAG.hasCycle()` 正确检测循环依赖
- [ ] `TaskScheduler.schedule()` 按策略排序任务
- [ ] `TaskManager.loadTasks()` 能加载 tasks.json
- [ ] 所有单元测试通过

---

## 需求满足追溯

| 需求 | 实现文件 | 验证方法 |
|------|----------|----------|
| R1.1 | `TaskManager.ts` | `loadTasks()` 成功加载 |
| R1.2 | `TaskDAG.ts` | `topologicalSort()` 正确 |
| R1.3 | `TaskDAG.ts` | `getReadyTasks()` 返回并行任务 |
| R1.4 | `TaskScheduler.ts` | `getNextTask()` 返回下一个任务 |
| R1.5 | `TaskScheduler.ts` | `sortByPriority()` 正确排序 |

---

## 快速导航

- ← [Phase 0-1](04-phase-0-1.md)
- → [Phase 3: Layer 3 执行层](06-phase-3-execution.md)
- [返回索引](00-index.md)
