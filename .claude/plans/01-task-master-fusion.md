# Task Master 深度融合方案

> 返回 [索引](00-index.md)

## 核心架构发现

> ✅ 2025-12-08 深度探索完成

| 组件 | 状态 | 说明 |
|------|------|------|
| TaskDAG | ❌ 不存在独立类 | 依赖管理在 `dependency-manager.js` |
| TaskScheduler | ❌ 不存在独立类 | 调度逻辑在 `task-service.ts` |
| WorkflowOrchestrator | ✅ 核心 | TDD 状态机（RED-GREEN-COMMIT）|
| Direct Functions | ✅ 最有价值 | 41 个核心业务函数 |
| MCP 工具 | ✅ 43 个工具 | 完整的 Claude 集成 |

---

## 必须融合的组件

### Direct Functions

```
claude-task-master/mcp-server/src/core/direct-functions/
├── parse-prd.js          ← PRD → 任务列表
├── expand-task.js        ← 任务 → 子任务
├── add-task.js           ← AI 生成任务
├── analyze-task-complexity.js  ← 复杂度分析
├── next-task.js          ← 下一个任务算法
└── update-tasks.js       ← 批量更新
```

### 状态机

```
claude-task-master/packages/tm-core/src/modules/workflow/
├── orchestrators/workflow-orchestrator.ts  ← TDD 状态机
├── managers/workflow-state-manager.ts      ← 状态持久化
└── services/workflow.service.ts            ← 工作流服务
```

---

## 融合策略

1. **保留** `.taskmaster/tasks/tasks.json` 格式
2. **复用** Direct Functions（parsePRDDirect, expandTaskDirect 等）
3. **适配** WorkflowOrchestrator 到多 Worker 并行
4. **复用** MCP 工具注册模式（withToolContext HOF）
5. **重命名** TaskMasterAdapter → TaskManager

---

## WorkflowOrchestrator 多 Worker 适配

### task-master 原始设计（单 Agent）

```
┌─────────────────────────────────────────────────────────┐
│                  WorkflowOrchestrator                   │
│  PREFLIGHT → BRANCH_SETUP → SUBTASK_LOOP → FINALIZE    │
│                        ↓                                │
│              TDD: RED → GREEN → COMMIT                  │
│                   (单个 Claude 执行)                     │
└─────────────────────────────────────────────────────────┘
```

### ParallelDev 适配设计（多 Worker）

```
┌─────────────────────────────────────────────────────────┐
│                  MasterOrchestrator                     │
│  • 管理多个 WorkerOrchestrator 实例                      │
│  • 任务分配和负载均衡                                    │
│  • 全局状态同步                                          │
└─────────────────────────────────────────────────────────┘
          ↓              ↓              ↓
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Worker 1   │  │  Worker 2   │  │  Worker 3   │
│ Orchestrator│  │ Orchestrator│  │ Orchestrator│
│ TDD Loop    │  │ TDD Loop    │  │ TDD Loop    │
│ (独立执行)   │  │ (独立执行)   │  │ (独立执行)   │
└─────────────┘  └─────────────┘  └─────────────┘
     Task A          Task B          Task C
```

### 关键改造点

| task-master 原始 | ParallelDev 改造 | 说明 |
|-----------------|-----------------|------|
| 单一 WorkflowContext | 多个 WorkerContext | 每个 Worker 独立上下文 |
| 全局 currentPhase | Worker 级别 phase | 每个 Worker 独立状态机 |
| 单一 subtasks 队列 | 分布式任务队列 | Master 统一调度 |
| 同步状态转换 | 异步事件驱动 | Socket.IO 通信 |

### 爆改代码映射

```typescript
// 源文件: workflow-orchestrator.ts:38-44
// 原始：单一上下文
constructor(initialContext: WorkflowContext) {
  this.currentPhase = 'PREFLIGHT';
  this.context = { ...initialContext };
}

// 爆改：Worker 级别上下文
// 目标文件: src/parallel/worker/WorkerOrchestrator.ts
export class WorkerOrchestrator {
  private workerId: string;
  private currentPhase: WorkflowPhase = 'READY';
  private context: WorkerContext;
  private masterConnection: SocketClient;

  constructor(workerId: string, masterUrl: string) {
    this.workerId = workerId;
    this.masterConnection = new SocketClient(masterUrl, workerId);
  }
}
```

---

## Direct Functions 集成方案

### 36 个 Direct Functions 分类

| 类别 | 函数名 | ParallelDev 集成位置 |
|------|--------|---------------------|
| **任务获取** | `nextTaskDirect` | TaskScheduler.getNextTask() |
| **任务扩展** | `expandTaskDirect` | TaskManager.expandTask() |
| **PRD 解析** | `parsePrdDirect` | TaskManager.parsePRD() |
| **复杂度分析** | `analyzeTaskComplexityDirect` | TaskManager.analyzeComplexity() |
| **状态更新** | `setTaskStatusDirect` | TaskManager.setStatus() |
| **依赖管理** | `addDependencyDirect`, `validateDependenciesDirect` | TaskDAG |
| **子任务管理** | `addSubtaskDirect`, `updateSubtaskDirect` | TaskManager |

### Direct Function 模式爆改

```javascript
// 源文件: next-task.js:27-42 (task-master 模式)
export async function nextTaskDirect(args, log, context = {}) {
  const { tasksJsonPath, reportPath, projectRoot, tag } = args;
  const { session } = context;

  if (!tasksJsonPath) {
    return {
      success: false,
      error: { code: 'MISSING_ARGUMENT', message: 'tasksJsonPath is required' }
    };
  }
  // ...
}

// 爆改：TypeScript + ParallelDev 模式
// 目标文件: src/parallel/task/TaskManager.ts
export class TaskManager {
  async getNextTask(options: GetNextTaskOptions): Promise<TaskResult<Task>> {
    const { tasksJsonPath, workerId, excludeAssigned } = options;

    if (!tasksJsonPath) {
      return {
        success: false,
        error: { code: 'MISSING_ARGUMENT', message: 'tasksJsonPath is required' }
      };
    }

    // 额外：排除已分配给其他 Worker 的任务
    const tasks = await this.loadTasks(tasksJsonPath);
    const availableTasks = excludeAssigned
      ? tasks.filter(t => !t.assignedWorker || t.assignedWorker === workerId)
      : tasks;

    return this.scheduler.getNextTask(availableTasks);
  }
}
```

---

## TDD 状态机简化方案

### task-master TDD 完整流程

```
PREFLIGHT → BRANCH_SETUP → SUBTASK_LOOP → FINALIZE → COMPLETE
                              ↓
                    RED → GREEN → COMMIT
                    (测试驱动开发循环)
```

### ParallelDev 简化流程

```
READY → ASSIGNED → RUNNING → VALIDATING → COMPLETED/FAILED
                      ↓
              (Worker 执行任务)
              (可选：TDD 子循环)
```

**原因**：
- ParallelDev 关注 **任务并行执行**，不强制 TDD
- TDD 是 Worker 内部可选行为
- 简化 Master-Worker 通信协议

### 状态转换事件映射

| task-master 事件 | ParallelDev 事件 | 触发条件 |
|-----------------|------------------|---------|
| `PREFLIGHT_COMPLETE` | `WORKER_READY` | Worker 初始化完成 |
| `BRANCH_CREATED` | `TASK_ASSIGNED` | Master 分配任务 |
| `RED_PHASE_COMPLETE` | (内部) | Worker TDD 可选 |
| `GREEN_PHASE_COMPLETE` | (内部) | Worker TDD 可选 |
| `COMMIT_COMPLETE` | `TASK_COMPLETED` | Worker 完成任务 |
| `ALL_SUBTASKS_COMPLETE` | `ALL_TASKS_DONE` | 所有任务完成 |

---

## 核心文件爆改清单

### Phase 0a: 从 task-master 爆改

| 源文件 | 行数 | 目标文件 | 爆改内容 |
|--------|------|----------|----------|
| `dependency-manager.js:379-527` | 150 | `TaskDAG.ts` | 循环检测、依赖验证 |
| `task-manager/find-next-task.js` | 200 | `TaskScheduler.ts` | 下一个任务算法 |
| `direct-functions/next-task.js` | 140 | `TaskManager.ts` | nextTask 函数模式 |
| `direct-functions/expand-task.js` | 265 | `TaskManager.ts` | expandTask 函数模式 |
| `workflow-orchestrator.ts:150-291` | 140 | `WorkerOrchestrator.ts` | TDD 状态转换 |

### Phase 0b: 从 Happy 爆改

| 源文件 | 目标文件 | 爆改内容 |
|--------|----------|----------|
| `happy/sources/sync/apiSocket.ts` | `SocketClient.ts` | 移除加密，Worker 通信 |
| `happy-cli/src/api/rpc/RpcHandlerManager.ts` | `RpcManager.ts` | 简化 RPC 管理 |

---

## 类型定义同步

```typescript
// 源文件: packages/tm-core/src/common/types/index.ts
// 目标文件: src/parallel/types.ts

// Task 类型（必须兼容 tasks.json）
export interface Task {
  id: number | string;
  title: string;
  description: string;
  status: TaskStatus;
  dependencies: (number | string)[];
  priority?: 'low' | 'medium' | 'high' | 'critical';
  subtasks?: Subtask[];
  // ParallelDev 扩展
  assignedWorker?: string;
  worktreePath?: string;
  startedAt?: string;
  completedAt?: string;
}

// 状态类型（保持兼容）
export type TaskStatus =
  | 'pending'      // task-master
  | 'in-progress'  // task-master
  | 'done'         // task-master
  | 'deferred'     // task-master
  | 'cancelled'    // task-master
  | 'blocked'      // task-master
  // ParallelDev 扩展
  | 'ready'        // 依赖已满足
  | 'running'      // Worker 执行中
  | 'completed'    // 等同于 done
  | 'failed';      // 执行失败
```

---

## 6 层架构映射

| ParallelDev Layer | task-master 对应组件 | 爆改策略 |
|-------------------|---------------------|---------|
| Layer 1: Task Management | dependency-manager.js, task-service.ts | 提取 DAG 算法 |
| Layer 2: Orchestration | workflow-orchestrator.ts | 适配多 Worker |
| Layer 3: Execution | (无对应) | 新建 |
| Layer 4: Communication | (无对应，用 Happy) | 爆改 Happy |
| Layer 5: Quality | test-result-validator.ts | 参考测试验证 |
| Layer 6: Notification | (无对应) | 新建 |

---

## 方案对比

### 方案 A：纯爆改（不使用 MCP）

```
ParallelDev 内置爆改代码
├── TaskDAG.ts         ← 爆改 dependency-manager.js
├── TaskScheduler.ts   ← 爆改 task-service.ts
├── TaskManager.ts     ← 爆改 direct-functions/*.js
└── 无外部 MCP 依赖
```

**优点**：无外部依赖，完全自包含，可针对并行场景优化
**缺点**：需要手动跟踪 task-master 更新

### 方案 B：使用 task-master MCP

**优点**：复用完整功能，自动享受更新
**缺点**：需要额外进程，增加复杂度

### 方案 C：混合方案

核心调度逻辑爆改内置，AI 增强功能可选使用 MCP

### 方案 D：全栈爆改方案（最终选择）

> 🔴 **用户确认**：即使是 MCP 功能也需要爆改自己实现

**核心思路**：
- 全部爆改：核心逻辑 + MCP 工具代码都从 task-master 提取
- 自建 MCP 服务：ParallelDev 作为独立 MCP 服务器
- 完全控制：可针对并行场景深度优化

---

## 方案 D 详细设计

### 架构

```
┌─────────────────────────────────────────────────────────┐
│                 ParallelDev MCP Server                  │
│  ┌────────────────────────────────────────────────┐    │
│  │  核心层（爆改自 task-master）                    │    │
│  │  • TaskDAG ← dependency-manager.js             │    │
│  │  • TaskScheduler ← task-service.ts             │    │
│  │  • TaskManager ← direct-functions/*.js         │    │
│  └────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────┐    │
│  │  MCP 工具层（爆改自 task-master MCP）           │    │
│  │  • parallel_next_task                          │    │
│  │  • parallel_expand_task                        │    │
│  │  • parallel_assign_task                        │    │
│  │  • parallel_worker_status                      │    │
│  └────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────┐    │
│  │  并行执行层（新增）                              │    │
│  │  • MasterOrchestrator                          │    │
│  │  • WorkerPool                                  │    │
│  │  • Socket.IO 通信（爆改自 Happy）               │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### MCP 工具爆改清单

| task-master MCP 工具 | ParallelDev 爆改 | 改动说明 |
|---------------------|-----------------|---------|
| `next_task` | `parallel_next_task` | 增加 Worker 排除、并行获取 |
| `expand_task` | `parallel_expand_task` | 增加并行子任务生成 |
| `set_task_status` | `parallel_set_status` | 增加 Worker 分配状态 |
| `get_task` | `parallel_get_task` | 增加 worktree 路径 |
| (无) | `parallel_assign_task` | 新增：分配任务给 Worker |
| (无) | `parallel_worker_status` | 新增：Worker 状态查询 |
| (无) | `parallel_start` | 新增：启动并行执行 |
| (无) | `parallel_stop` | 新增：停止执行 |

### 文件结构

```
src/parallel/
├── types.ts                    # 核心类型（兼容 task-master）
├── config.ts                   # 配置
├── task/                       # Layer 1: 任务管理
│   ├── TaskDAG.ts              # 爆改自 dependency-manager.js
│   ├── TaskScheduler.ts        # 爆改自 task-service.ts
│   ├── TaskManager.ts          # 任务管理器
│   └── handlers/               # MCP 工具处理器
├── master/                     # Layer 2: 编排
│   ├── MasterOrchestrator.ts
│   ├── WorkerPool.ts
│   └── StateManager.ts
├── worker/                     # Layer 3: 执行
│   ├── WorkerOrchestrator.ts   # 爆改自 workflow-orchestrator.ts
│   ├── TaskExecutor.ts
│   └── StatusReporter.ts
├── communication/              # Layer 4: 通信（爆改自 Happy）
├── quality/                    # Layer 5: 质量
├── notification/               # Layer 6: 通知
└── mcp/                        # MCP 服务器
```

---

**优点**：
- ✅ 完全控制所有代码
- ✅ 可深度优化并行场景
- ✅ 无外部运行时依赖
- ✅ AI 功能直接集成，不依赖 task-master MCP

**缺点**：
- ❌ 初始工作量较大
- ❌ 需要维护 Claude API 集成代码

---

> 下一步: [通信层深度爆改方案](02-communication-layer.md)
