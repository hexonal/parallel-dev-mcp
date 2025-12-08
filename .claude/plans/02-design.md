# Phase 0a/0b: 爆改设计方案

> 返回 [索引](00-index.md) | 上一篇: [准备工作](01-preparation.md)

> 本文档基于 [01-preparation.md](01-preparation.md) 中的源码分析结果

---

## TODO 完成规范

> **重要**：每个 TODO 小点完成后，执行以下流程：
> 1. 使用 task agent 进行自测验证
> 2. 询问用户是否提交推送代码
> 3. 如用户同意，执行 `git add -A && git commit && git push`

---

## Part A: Task Master 融合方案

### 融合策略

基于 [源码分析结果](01-preparation.md#源码分析结果)：

1. **保留** `.taskmaster/tasks/tasks.json` 格式
2. **复用** Direct Functions（parsePRDDirect, expandTaskDirect 等）
3. **适配** WorkflowOrchestrator 到多 Worker 并行
4. **复用** MCP 工具注册模式（withToolContext HOF）
5. **重命名** TaskMasterAdapter → TaskManager

---

### WorkflowOrchestrator 多 Worker 适配

#### task-master 原始设计（单 Agent）

```
┌─────────────────────────────────────────────────────────┐
│                  WorkflowOrchestrator                   │
│  PREFLIGHT → BRANCH_SETUP → SUBTASK_LOOP → FINALIZE    │
│                        ↓                                │
│              TDD: RED → GREEN → COMMIT                  │
│                   (单个 Claude 执行)                     │
└─────────────────────────────────────────────────────────┘
```

#### ParallelDev 适配设计（多 Worker）

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

#### 关键改造点

| task-master 原始 | ParallelDev 改造 | 说明 |
|-----------------|-----------------|------|
| 单一 WorkflowContext | 多个 WorkerContext | 每个 Worker 独立上下文 |
| 全局 currentPhase | Worker 级别 phase | 每个 Worker 独立状态机 |
| 单一 subtasks 队列 | 分布式任务队列 | Master 统一调度 |
| 同步状态转换 | 异步事件驱动 | Socket.IO 通信 |

---

### Direct Functions 集成方案

#### 36 个 Direct Functions 分类

| 类别 | 函数名 | ParallelDev 集成位置 |
|------|--------|---------------------|
| **任务获取** | `nextTaskDirect` | TaskScheduler.getNextTask() |
| **任务扩展** | `expandTaskDirect` | TaskManager.expandTask() |
| **PRD 解析** | `parsePrdDirect` | TaskManager.parsePRD() |
| **复杂度分析** | `analyzeTaskComplexityDirect` | TaskManager.analyzeComplexity() |
| **状态更新** | `setTaskStatusDirect` | TaskManager.setStatus() |
| **依赖管理** | `addDependencyDirect`, `validateDependenciesDirect` | TaskDAG |
| **子任务管理** | `addSubtaskDirect`, `updateSubtaskDirect` | TaskManager |

---

### TDD 状态机简化方案

#### task-master TDD 完整流程

```
PREFLIGHT → BRANCH_SETUP → SUBTASK_LOOP → FINALIZE → COMPLETE
                              ↓
                    RED → GREEN → COMMIT
                    (测试驱动开发循环)
```

#### ParallelDev 简化流程

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

---

### 方案选择：方案 D（全栈爆改）

> 用户确认：即使是 MCP 功能也需要爆改自己实现

**核心思路**：
- 全部爆改：核心逻辑 + MCP 工具代码都从 task-master 提取
- 自建 MCP 服务：ParallelDev 作为独立 MCP 服务器
- 完全控制：可针对并行场景深度优化

#### MCP 工具爆改清单

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

---

### 核心文件爆改清单

#### 从 task-master 爆改

| 源文件 | 行数 | 目标文件 | 爆改内容 |
|--------|------|----------|----------|
| `dependency-manager.js:379-527` | 150 | `TaskDAG.ts` | 循环检测、依赖验证 |
| `task-manager/find-next-task.js` | 200 | `TaskScheduler.ts` | 下一个任务算法 |
| `direct-functions/next-task.js` | 140 | `TaskManager.ts` | nextTask 函数模式 |
| `direct-functions/expand-task.js` | 265 | `TaskManager.ts` | expandTask 函数模式 |
| `workflow-orchestrator.ts:150-291` | 140 | `WorkerOrchestrator.ts` | TDD 状态转换 |

#### 从 Happy 爆改

> **爆改目标**：在保留加密的基础上，添加**父子进程双向 RPC 调用**能力

| 源文件 | 行数 | 目标文件 | 爆改内容 |
|--------|------|----------|----------|
| `happy/sources/sync/apiSocket.ts` | 262 | `SocketClient.ts` | 添加双向 RPC、请求-响应匹配 |
| `happy-cli/src/api/rpc/RpcHandlerManager.ts` | 135 | `RpcManager.ts` | 添加父→子调用、子→父回复 |

**爆改原因**：
- Happy 当前是 Client→Server 单向模式
- ParallelDev 需要 Master↔Worker 双向调用
- 需要请求 ID 追踪（匹配请求和响应）
- 保留 TweetNaCl 加密（支持未来远程 Worker）

---

## Part B: 通信层深度爆改方案（Layer 4）

> **爆改目标**：在保留加密的基础上，实现**父子进程双向 RPC 调用**

---

### Happy 原始通信架构（单向）

```
┌──────────────────────────────────────────────────────────────────┐
│                    Happy 原始架构（单向）                          │
│  ┌─────────────┐     Socket.IO      ┌─────────────────────────┐ │
│  │  apiSocket  │ ────────────────→ │  Server                 │ │
│  │  (Client)   │                    │                         │ │
│  └─────────────┘                    └─────────────────────────┘ │
│                                                                  │
│  ⚠️ 局限性:                                                      │
│  • 只支持 Client → Server 单向 RPC                               │
│  • Server 无法主动调用 Client 方法                                │
│  • 无法满足 Master↔Worker 双向通信需求                            │
└──────────────────────────────────────────────────────────────────┘
```

---

### ParallelDev 爆改架构（双向 RPC）

```
┌──────────────────────────────────────────────────────────────────┐
│                  ParallelDev 通信架构（爆改后）                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              MasterSocketServer（爆改，双向 RPC）             ││
│  │  • 监听 Worker 连接                                         ││
│  │  • 主动调用 Worker RPC（父→子）                              ││
│  │  • 响应 Worker RPC 调用（子→父）                              ││
│  │  • 请求 ID 追踪（匹配请求和响应）                              ││
│  └─────────────────────────────────────────────────────────────┘│
│              ↕                    ↕                    ↕         │
│          Worker 1             Worker 2             Worker 3      │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      │
│  │SocketClient │      │SocketClient │      │SocketClient │      │
│  │(爆改apiSocket)     │(爆改apiSocket)     │(爆改apiSocket)     │
│  │ +双向RPC    │      │ +双向RPC    │      │ +双向RPC    │      │
│  └─────────────┘      └─────────────┘      └─────────────┘      │
│                                                                  │
│  爆改后特性:                                                      │
│  ✅ 保留加密（TweetNaCl）                                        │
│  ✅ Master → Worker RPC（父调用子）                              │
│  ✅ Worker → Master RPC（子调用父/子回复父）                      │
│  ✅ 请求 ID 追踪（匹配请求-响应）                                  │
│  ✅ 超时处理和重试机制                                            │
└──────────────────────────────────────────────────────────────────┘
```

---

### SocketClient 爆改（Worker 端）

**源文件**: `happy/sources/sync/apiSocket.ts` (262 行)
**目标文件**: `src/parallel/communication/SocketClient.ts`

#### 爆改对照表

| Happy 原始 | 爆改操作 | 说明 |
|-----------|---------|------|
| `sessionRPC()` | ✅ 保留 + 扩展 | 添加请求 ID 追踪 |
| `machineRPC()` | ✅ 保留 | 可用于 Master 通信 |
| `Encryption` | ✅ 保留 | 保持端到端加密 |
| `TokenStorage` | ✅ 保留 | 可用于 Worker 认证 |
| (无) | ⭐ 新增 `registerHandler()` | 注册可被远程调用的方法 |
| (无) | ⭐ 新增 `onRpcRequest()` | 监听来自 Master 的 RPC 调用 |
| (无) | ⭐ 新增 `respond()` | 响应 RPC 调用 |

**爆改实现**:
```typescript
// src/parallel/communication/SocketClient.ts
// 爆改自 happy/sources/sync/apiSocket.ts

export class SocketClient {
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private handlers: Map<string, RpcHandler> = new Map();

  // 保留：加密 RPC 调用（子→父）
  async rpc<T>(method: string, params: unknown): Promise<T>;

  // ⭐ 新增：注册本地处理器（父→子调用时触发）
  registerHandler(method: string, handler: RpcHandler): void;

  // ⭐ 新增：响应 RPC 请求
  private respond(requestId: string, result: unknown): void;

  // ⭐ 新增：处理来自 Master 的 RPC 调用
  private handleRpcRequest(request: RpcRequest): void;
}

interface RpcRequest {
  id: string;           // 请求 ID（用于匹配响应）
  method: string;       // 方法名
  params: unknown;      // 参数
  timestamp: number;    // 时间戳
}
```

---

### RpcManager 爆改

**源文件**: `happy-cli/src/api/rpc/RpcHandlerManager.ts` (135 行)
**目标文件**: `src/parallel/communication/RpcManager.ts`

#### 爆改对照表

| Happy 原始 | 爆改操作 | 说明 |
|-----------|---------|------|
| `encryptionKey` | ✅ 保留 | 保持加密 |
| `encrypt()/decrypt()` | ✅ 保留 | 保持加密传输 |
| `registerHandler()` | ✅ 保留 | 注册处理器 |
| (无) | ⭐ 新增 `callWorker()` | Master 调用 Worker |
| (无) | ⭐ 新增 `callMaster()` | Worker 调用 Master |
| (无) | ⭐ 新增 `waitResponse()` | 等待响应（带超时） |

**爆改实现**:
```typescript
// src/parallel/communication/RpcManager.ts
// 爆改自 happy-cli/src/api/rpc/RpcHandlerManager.ts

export class RpcManager {
  private pendingRequests: Map<string, PendingRequest> = new Map();

  // 保留：加密配置
  constructor(encryptionKey: string);

  // 保留：注册处理器
  registerHandler(method: string, handler: RpcHandler): void;

  // ⭐ 新增：Master 调用 Worker
  async callWorker<T>(workerId: string, method: string, params: unknown): Promise<T>;

  // ⭐ 新增：Worker 调用 Master（或回复）
  async callMaster<T>(method: string, params: unknown): Promise<T>;

  // ⭐ 新增：等待响应
  private waitResponse<T>(requestId: string, timeoutMs: number): Promise<T>;

  // ⭐ 新增：生成请求 ID
  private generateRequestId(): string;
}
```

---

### 通信协议定义

**目标文件**: `src/parallel/communication/types.ts`

```typescript
// ============ 连接状态 ============
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

// ============ Master → Worker 命令 ============
export type MasterCommandType =
  | 'assign_task' | 'cancel_task' | 'request_status'
  | 'shutdown' | 'pause' | 'resume';

export interface MasterCommand {
  type: MasterCommandType;
  payload: unknown;
  timestamp: string;
}

// ============ Worker → Master 事件 ============
export type WorkerEventType =
  | 'ready' | 'task_started' | 'task_progress'
  | 'task_completed' | 'task_failed' | 'status_update' | 'log' | 'error';

export interface WorkerEvent {
  type: WorkerEventType;
  workerId: string;
  payload: unknown;
  timestamp: string;
}
```

---

### 通信层文件结构

```
src/parallel/communication/
├── index.ts                    # 导出
├── types.ts                    # 协议类型定义
├── SocketClient.ts             # Worker 客户端（爆改自 apiSocket.ts）
├── SocketServer.ts             # Master 服务器（爆改，支持双向 RPC）
└── rpc/
    ├── index.ts
    ├── RpcManager.ts           # RPC 管理器（爆改自 RpcHandlerManager.ts）
    └── types.ts                # RPC 类型

# 爆改来源
happy/sources/sync/apiSocket.ts          → SocketClient.ts
happy-cli/src/api/rpc/RpcHandlerManager.ts  → RpcManager.ts
```

---

## Part C: 类型定义同步

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

## Part D: 6 层架构映射

| ParallelDev Layer | task-master 对应组件 | 爆改策略 |
|-------------------|---------------------|---------|
| Layer 1: Task Management | dependency-manager.js, task-service.ts | 提取 DAG 算法 |
| Layer 2: Orchestration | workflow-orchestrator.ts | 适配多 Worker |
| Layer 3: Execution | (无对应) | 新建 |
| Layer 4: Communication | (无对应，用 Happy) | 爆改 Happy |
| Layer 5: Quality | test-result-validator.ts | 参考测试验证 |
| Layer 6: Notification | (无对应) | 新建 |

---

## 最终文件结构

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
│   ├── SocketClient.ts
│   ├── SocketServer.ts
│   └── rpc/
├── quality/                    # Layer 5: 质量
├── notification/               # Layer 6: 通知
└── mcp/                        # MCP 服务器
```

---

## 快速导航

- ← [准备工作](01-preparation.md)
- → [验证策略](03-verification.md)
- [返回索引](00-index.md)
