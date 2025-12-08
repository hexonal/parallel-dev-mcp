# Phase 4-8：通信/质量/编排/通知/集成

> 本文件包含 ParallelDev 后续阶段实施细节

---

## TODO 完成规范

> **🔴 重要**：每个 TODO 小点完成后，执行以下流程：
> 1. 使用 task agent 进行自测验证
> 2. 询问用户是否提交推送代码
> 3. 如用户同意，执行 `git add -A && git commit && git push`

---

## Phase 4: Layer 4 通信层（爆改 Happy）

**目标**：爆改 Happy 通信层实现 Master-Worker **双向 RPC 通信**，满足需求：
- R4.1: Master-Worker 通信 (Socket.IO + RPC)
- R4.2: 事件驱动架构
- R4.3: Worker 完成任务时触发新任务分配

**爆改策略**：
- ✅ 爆改 Happy 的 `apiSocket.ts` → 添加双向 RPC、请求-响应匹配
- ✅ 爆改 Happy 的 `RpcHandlerManager.ts` → 添加父→子调用、子→父回复
- ✅ 保留 TweetNaCl 加密（支持未来远程 Worker）

**爆改原因**：
- Happy 当前是 Client→Server **单向** RPC
- ParallelDev 需要 Master↔Worker **双向** RPC（父子进程互调）

### TODO 4.1: 爆改 SocketClient.ts

**文件**: `src/parallel/communication/SocketClient.ts`

**爆改来源**: `happy/sources/sync/apiSocket.ts` (262 行)

**核心接口**：
```typescript
/**
 * 爆改自 happy/sources/sync/apiSocket.ts
 * 新增：双向 RPC、请求 ID 追踪、处理器注册
 */
export class SocketClient {
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private handlers: Map<string, RpcHandler> = new Map();

  // 保留：连接管理
  connect(url: string): Promise<void>;
  disconnect(): void;
  isConnected(): boolean;

  // 保留：加密 RPC 调用（子→父）
  async rpc<T>(method: string, params: unknown): Promise<T>;

  // ⭐ 新增：注册本地处理器（父→子调用时触发）
  registerHandler(method: string, handler: RpcHandler): void;
  unregisterHandler(method: string): void;

  // ⭐ 新增：处理来自 Master 的 RPC 调用
  private handleRpcRequest(request: RpcRequest): Promise<void>;

  // ⭐ 新增：响应 RPC 请求
  private respond(requestId: string, result: unknown, error?: string): void;
}

interface RpcRequest {
  id: string;           // 请求 ID（用于匹配响应）
  method: string;       // 方法名
  params: unknown;      // 参数
  timestamp: number;    // 时间戳
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 4.2: 实现 SocketServer.ts

**文件**: `src/parallel/communication/SocketServer.ts`

**核心接口**：
```typescript
export class SocketServer extends EventEmitter {
  constructor(port: number);
  start(): Promise<void>;
  stop(): Promise<void>;
  broadcast(event: string, data: any): void;
  sendToWorker(workerId: string, event: string, data: any): void;
  getConnectedWorkers(): string[];
}

// 事件类型
// 'worker:register' | 'worker:heartbeat' | 'worker:task_started' |
// 'worker:task_completed' | 'worker:task_failed'
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 4.3: 实现 StatusReporter.ts

**文件**: `src/parallel/worker/StatusReporter.ts`

**核心接口**：
```typescript
export class StatusReporter {
  constructor(socket: SocketClient, workerId: string);
  reportTaskStarted(taskId: string): void;
  reportTaskCompleted(taskId: string, result: TaskResult): void;
  reportTaskFailed(taskId: string, error: string): void;
  reportProgress(taskId: string, progress: number, message?: string): void;
  startHeartbeat(intervalMs?: number): void;
  stopHeartbeat(): void;
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 4.4: 爆改 RpcManager.ts

**文件**: `src/parallel/communication/RpcManager.ts`

**爆改来源**: `happy-cli/src/api/rpc/RpcHandlerManager.ts` (135 行)

**核心接口**：
```typescript
/**
 * 爆改自 happy-cli/src/api/rpc/RpcHandlerManager.ts
 * 新增：双向 RPC、请求 ID 追踪、超时处理
 */
export class RpcManager {
  private pendingRequests: Map<string, PendingRequest> = new Map();

  // 保留：加密配置
  constructor(encryptionKey?: string);

  // 保留：注册处理器
  registerHandler(method: string, handler: RpcHandler): void;
  unregisterHandler(method: string): void;

  // ⭐ 新增：Master 调用 Worker（父→子）
  async callWorker<T>(workerId: string, method: string, params: unknown): Promise<T>;

  // ⭐ 新增：Worker 调用 Master（子→父）
  async callMaster<T>(method: string, params: unknown): Promise<T>;

  // ⭐ 新增：等待响应（带超时）
  private waitResponse<T>(requestId: string, timeoutMs: number): Promise<T>;

  // ⭐ 新增：生成请求 ID
  private generateRequestId(): string;

  // ⭐ 新增：处理响应
  handleResponse(requestId: string, result: unknown, error?: string): void;
}

interface PendingRequest {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  timeout: NodeJS.Timeout;
}
```

**完成后**：task agent 自测 → 询问是否提交推送

**Phase 4 验收标准**：
- [ ] SocketClient 双向 RPC 正常（爆改 apiSocket）
- [ ] RpcManager 双向调用正常（爆改 RpcHandlerManager）
- [ ] TweetNaCl 加密功能保留
- [ ] Master → Worker RPC 调用正常（父→子）
- [ ] Worker → Master RPC 调用正常（子→父）
- [ ] 请求-响应匹配正常（请求 ID 追踪）

---

## Phase 5: Layer 5 质量保证层

**目标**：实现代码质量检查和冲突解决，满足需求：
- R5.1: 分层冲突解决（Level 1-3，>70% 自动解决）
- R5.2: 自动测试
- R5.3: Lint 检查
- R5.4: 类型检查
- R5.5: 质量门禁

### TODO 5.1: 实现 SubagentRunner.ts

**文件**: `src/parallel/quality/SubagentRunner.ts`

**核心接口**：
```typescript
export class SubagentRunner {
  constructor(projectRoot: string);

  /**
   * 运行 Subagent
   * @param agentName Agent 名称（quality-gate, conflict-resolver 等）
   * @param prompt 执行提示
   * @param model 模型选择（sonnet | haiku）
   */
  async run(agentName: string, prompt: string, model?: 'sonnet' | 'haiku'): Promise<{
    success: boolean;
    output: string;
    error?: string;
  }>;

  /**
   * 运行质量检查 Agent
   */
  async runQualityGate(worktreePath: string): Promise<QualityCheckResult>;

  /**
   * 运行冲突解决 Agent
   */
  async runConflictResolver(worktreePath: string, conflicts: ConflictInfo[]): Promise<ResolveResult>;
}

export interface QualityCheckResult {
  passed: boolean;
  typeCheck: { passed: boolean; errors: string[] };
  lint: { passed: boolean; errors: string[] };
  tests: { passed: boolean; failures: string[] };
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 5.2: 实现 ConflictResolver.ts

**文件**: `src/parallel/quality/ConflictResolver.ts`

**核心接口**：
```typescript
export class ConflictResolver {
  constructor(detector: ConflictDetector, subagent: SubagentRunner);

  /**
   * 分层解决冲突
   */
  async resolve(worktreePath: string): Promise<ResolveResult>;

  /**
   * Level 1: 自动解决（lockfiles, 格式化）
   */
  private async resolveLevel1(conflicts: ConflictInfo[]): Promise<boolean>;

  /**
   * Level 2: AI 辅助解决
   */
  private async resolveLevel2(conflicts: ConflictInfo[]): Promise<boolean>;

  /**
   * Level 3: 标记需要人工介入
   */
  private markForHumanReview(conflicts: ConflictInfo[]): void;
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 5.3: 实现 CodeValidator.ts

**文件**: `src/parallel/quality/CodeValidator.ts`

**核心接口**：
```typescript
export class CodeValidator {
  constructor(projectRoot: string);

  /**
   * 运行所有验证
   */
  async validate(worktreePath: string): Promise<ValidationResult>;

  /**
   * TypeScript 类型检查
   */
  async runTypeCheck(worktreePath: string): Promise<CheckResult>;

  /**
   * ESLint 检查
   */
  async runLint(worktreePath: string): Promise<CheckResult>;

  /**
   * 运行单元测试
   */
  async runTests(worktreePath: string): Promise<TestResult>;
}

export interface ValidationResult {
  passed: boolean;
  typeCheck: CheckResult;
  lint: CheckResult;
  tests: TestResult;
  summary: string;
}
```

**完成后**：task agent 自测 → 询问是否提交推送

**Phase 5 验收标准**：
- [ ] Subagent 可正常调用
- [ ] 冲突解决流程正常（Level 1/2/3）
- [ ] 代码验证流程正常（TypeScript + ESLint + Tests）

---

## Phase 6: Layer 2 编排层

**目标**：实现主控制器和状态管理，满足需求：
- R2.1: Master Orchestrator 主控制器
- R2.2: 任务调度
- R2.3: Worker 管理（创建、监控、销毁）
- R2.4: 状态监控

### TODO 6.1: 实现 MasterOrchestrator.ts

**文件**: `src/parallel/master/MasterOrchestrator.ts`

**核心接口**：
```typescript
export class MasterOrchestrator {
  constructor(config: ParallelDevConfig, projectRoot: string);

  /**
   * 启动编排器（事件驱动主循环）
   */
  async start(): Promise<void>;

  /**
   * 停止编排器
   */
  async stop(): Promise<void>;

  /**
   * 分配任务给 Worker
   */
  private async assignTask(worker: Worker, task: Task): Promise<void>;

  /**
   * 处理任务完成事件
   */
  private async handleTaskCompleted(event: WorkerEvent): Promise<void>;

  /**
   * 处理任务失败事件
   */
  private async handleTaskFailed(event: WorkerEvent): Promise<void>;

  /**
   * 尝试分配待执行任务（核心调度逻辑）
   */
  private async tryAssignTasks(): Promise<void>;

  /**
   * 检查是否所有任务完成
   */
  private isAllTasksCompleted(): boolean;

  /**
   * 生成完成报告并通知
   */
  private async finalize(): Promise<void>;
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 6.2: 实现 WorkerPool.ts

**文件**: `src/parallel/master/WorkerPool.ts`

**核心接口**：
```typescript
export class WorkerPool {
  constructor(maxWorkers: number);

  /**
   * 初始化 Worker 池
   */
  async initialize(projectRoot: string, config: ParallelDevConfig): Promise<void>;

  /**
   * 添加/移除 Worker
   */
  addWorker(worker: Worker): void;
  removeWorker(workerId: string): void;

  /**
   * 获取空闲 Worker
   */
  getIdleWorker(): Worker | undefined;

  /**
   * 设置/获取 Worker 状态
   */
  setWorkerStatus(workerId: string, status: WorkerStatus): void;
  getWorkerStatus(workerId: string): WorkerStatus | undefined;

  /**
   * 获取所有 Worker
   */
  getAllWorkers(): Worker[];

  /**
   * 获取统计信息
   */
  getStats(): { total: number; idle: number; busy: number; error: number };

  /**
   * 清理所有 Worker
   */
  async cleanup(): Promise<void>;

  /**
   * R7.1: Worker 崩溃恢复 ⭐ 新增
   */
  detectCrashedWorkers(): Worker[];
  async recoverWorker(workerId: string): Promise<boolean>;
  async restartWorker(workerId: string): Promise<Worker>;
  setRecoveryPolicy(policy: RecoveryPolicy): void;
}

export interface RecoveryPolicy {
  maxRetries: number;        // 最大重试次数（默认 3）
  retryDelayMs: number;      // 重试间隔（默认 5000）
  autoRecover: boolean;      // 是否自动恢复（默认 true）
}
```

**崩溃检测逻辑**：
- 心跳超时 > 90s
- Tmux 会话不存在
- Worktree 损坏

**恢复流程**：
1. 清理旧资源（Tmux/Worktree）
2. 重建 Worker
3. 重新分配失败的任务

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 6.3: 实现 StateManager.ts

**文件**: `src/parallel/master/StateManager.ts`

**核心接口**：
```typescript
export interface SystemState {
  workers: Worker[];
  tasks: Task[];
  currentPhase: 'idle' | 'running' | 'completed' | 'failed';
  startedAt: string | null;
  updatedAt: string | null;
  stats: SchedulerStats;
}

export class StateManager {
  constructor(projectRoot: string);

  /**
   * 保存/加载状态
   */
  async saveState(state: SystemState): Promise<void>;
  async loadState(): Promise<SystemState | null>;

  /**
   * 获取/更新/重置状态
   */
  getState(): SystemState;
  updateState(partial: Partial<SystemState>): void;
  resetState(): void;

  /**
   * 自动保存
   */
  startAutoSave(intervalMs?: number): void;
  stopAutoSave(): void;
}
```

**完成后**：task agent 自测 → 询问是否提交推送

**Phase 6 验收标准**：
- [ ] Master 编排流程正常（事件驱动）
- [ ] Worker 池管理正常
- [ ] 状态持久化正常
- [ ] Worker 崩溃恢复正常 (R7.1) ⭐ 新增

---

## Phase 7: Layer 6 通知层

**目标**：实现通知、监控和报告生成，满足需求：
- R6.1: 实时监控 Worker 状态
- R6.2: 任务进度显示
- R6.3: 资源使用监控 ⭐ 新增
- R6.4: 实时日志捕获 ⭐ 新增
- R6.5: 完成报告生成
- R6.6: 通知发送

### TODO 7.1: 实现 NotificationManager.ts

**文件**: `src/parallel/notification/NotificationManager.ts`

**核心接口**：
```typescript
export type NotificationChannel = 'terminal' | 'sound' | 'webhook';

export interface NotificationOptions {
  title: string;
  message: string;
  level: 'info' | 'success' | 'warning' | 'error';
  channels?: NotificationChannel[];
}

export class NotificationManager {
  constructor();

  /**
   * 发送通知
   */
  async notify(options: NotificationOptions): Promise<void>;

  /**
   * 设置活动通知渠道
   */
  setChannels(channels: NotificationChannel[]): void;

  /**
   * 任务相关通知
   */
  async notifyTaskCompleted(task: Task): Promise<void>;
  async notifyTaskFailed(task: Task, error: string): Promise<void>;
  async notifyAllCompleted(stats: SchedulerStats): Promise<void>;

  /**
   * 播放声音提示
   */
  private playSound(type: 'success' | 'error'): void;

  /**
   * 发送 Webhook
   */
  private async sendWebhook(url: string, payload: any): Promise<void>;
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 7.2: 实现 ReportGenerator.ts

**文件**: `src/parallel/notification/ReportGenerator.ts`

**核心接口**：
```typescript
export interface ExecutionReport {
  summary: {
    totalTasks: number;
    completedTasks: number;
    failedTasks: number;
    duration: string;
    startedAt: string;
    completedAt: string;
  };
  tasks: Array<{
    id: string;
    title: string;
    status: TaskStatus;
    duration?: string;
    worker?: string;
    error?: string;
  }>;
  workers: Array<{
    id: string;
    completedTasks: number;
    failedTasks: number;
  }>;
}

export class ReportGenerator {
  /**
   * 生成执行报告
   */
  generateReport(state: SystemState): ExecutionReport;

  /**
   * 格式化输出
   */
  formatMarkdown(report: ExecutionReport): string;
  formatJson(report: ExecutionReport): string;

  /**
   * 保存报告到文件
   */
  async saveReport(report: ExecutionReport, format: 'markdown' | 'json'): Promise<string>;
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 7.3: 实现 ResourceMonitor.ts ⭐ 新增

**文件**: `src/parallel/notification/ResourceMonitor.ts`

**满足需求**：
- R6.3: 资源使用监控
- R6.4: 实时日志捕获

**核心接口**：
```typescript
export interface ResourceReport {
  cpu: number;
  memory: { used: number; total: number; percent: number };
  disk: { used: number; total: number; percent: number };
  timestamp: string;
}

export interface LogEntry {
  timestamp: string;
  workerId: string;
  level: 'info' | 'warn' | 'error';
  message: string;
}

export class ResourceMonitor {
  constructor();

  /**
   * R6.3: 资源使用监控
   */
  async getCpuUsage(): Promise<number>;
  async getMemoryUsage(): Promise<{ used: number; total: number; percent: number }>;
  async getDiskUsage(path?: string): Promise<{ used: number; total: number; percent: number }>;

  /**
   * 获取综合资源报告
   */
  async getResourceReport(): Promise<ResourceReport>;

  /**
   * R6.4: 实时日志捕获
   */
  startLogCapture(workerId: string): void;
  stopLogCapture(workerId: string): void;
  getRecentLogs(workerId: string, lines?: number): string[];
  aggregateLogs(since?: Date): LogEntry[];

  /**
   * 日志流（用于实时显示）
   */
  onLog(handler: (entry: LogEntry) => void): void;
  offLog(handler: (entry: LogEntry) => void): void;
}
```

**实现要点**：
- 使用 `os` 模块获取 CPU/内存信息
- 使用 `fs.statfs` 获取磁盘使用情况
- 通过 Tmux capture-pane 捕获 Worker 日志
- 日志采用环形缓冲区存储（默认 1000 条）

**完成后**：task agent 自测 → 询问是否提交推送

**Phase 7 验收标准**：
- [ ] 通知功能正常（终端/声音）
- [ ] 报告生成正常（Markdown/JSON）
- [ ] 资源监控正常（CPU/内存/磁盘） ⭐ 新增
- [ ] 日志捕获正常 ⭐ 新增

---

## Phase 8: 集成测试 + CLI

**目标**：完整端到端测试，满足需求：
- R7.1: Worker 崩溃恢复
- R7.2: 任务失败重试
- R7.3: 心跳机制
- R7.4: 会话持久化

### TODO 8.1: 创建 CLI 入口

**文件**: `src/cli-parallel.ts`

**步骤**：
```bash
# 8.1.1 创建 CLI 文件
# 8.1.2 实现 run 命令
# 8.1.3 实现 status 命令
# 8.1.4 实现 stop 命令
# 8.1.5 测试 CLI 命令
node dist/cli-parallel.js --help
```

**CLI 命令**：

| 命令 | 描述 | 示例 |
|------|------|------|
| `run` | 启动并行执行 | `paralleldev run -w 3 -t tasks.json` |
| `status` | 查看状态 | `paralleldev status -f json` |
| `stop` | 停止执行 | `paralleldev stop --force` |
| `report` | 生成报告 | `paralleldev report -f markdown` |

**完成后**：task agent 自测（node dist/cli-parallel.js --help）→ 询问是否提交推送

### TODO 8.2: 端到端测试

**测试仓库**: `https://github.com/hexonal/test-demo`

**文件**: `src/parallel/__tests__/e2e.test.ts`

**步骤**：
```bash
# 8.2.1 克隆测试仓库
git clone https://github.com/hexonal/test-demo.git ./test-demo-e2e

# 8.2.2 创建任务文件
mkdir -p ./test-demo-e2e/.taskmaster/tasks
# 创建 tasks.json

# 8.2.3 运行测试
vitest run src/parallel/__tests__/e2e.test.ts
```

**测试场景**：

| 测试 | 验证内容 |
|------|----------|
| TaskManager | 正确加载任务文件 |
| TaskDAG | 正确检测循环依赖 |
| TaskScheduler | 正确排序任务 |
| WorktreeManager | 正确创建/删除 worktree |
| TmuxController | 正确创建/管理会话 |
| Full E2E | 完整执行流程 |

**完成后**：task agent 自测 → 询问是否提交推送

---

## Phase 8 验收标准

- [ ] CLI 命令正常工作
- [ ] 端到端测试通过
- [ ] 所有 27 项需求满足

---

## 最终验收标准

```
✅ 所有需求满足矩阵行状态为 ✅
✅ 所有验证脚本通过
✅ 系统端到端测试通过
✅ CLI 命令正常工作
```

---

## 快速导航

- ← [Phase 3: Layer 3 执行层](06-phase-3-exec.md)
- [返回索引](00-index.md)
- [验证策略](03-verification.md)
