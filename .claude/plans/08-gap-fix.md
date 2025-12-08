# 计划完整性修复方案

> 解决 plans 与 README 27 项需求的 GAP 问题

---

## 问题分析

经过系统性分析，当前 plans 覆盖率为 **86% (23/27)**，存在以下问题：

### 缺失覆盖 (2项)

| 需求 | 描述 | 来源 |
|------|------|------|
| R6.3 | 资源使用监控 (CPU/内存/磁盘) | README 核心特性-实时监控 |
| R6.4 | 实时日志捕获 | README 核心特性-实时监控 |

### 隐式覆盖 (2项)

| 需求 | 描述 | 问题 |
|------|------|------|
| R7.1 | Worker 崩溃恢复 | 无明确 TODO，应在 WorkerPool.ts |
| R7.2 | 任务失败重试 | 无明确 TODO，应在 TaskScheduler.ts |

### 文档不一致

- 03-verification.md 中的文件名与 Phase 计划不一致
- 需求矩阵缺失 R6.3, R6.4

---

## 修复步骤

### Step 1: 更新 07-phase-4-8.md - 添加 R6.3/R6.4

在 Phase 7 添加 TODO 7.3:

```markdown
### TODO 7.3: 实现 ResourceMonitor.ts

**文件**: `src/parallel/notification/ResourceMonitor.ts`

**核心接口**：
```typescript
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
}

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
```

**完成后**：task agent 自测 → 询问是否提交推送
```

### Step 2: 更新 05-phase-2-task.md - 添加 R7.2

在 TaskScheduler.ts 核心方法中添加：

```typescript
// R7.2: 任务失败重试
retryFailedTask(taskId: string): Promise<boolean>;
getRetryCount(taskId: string): number;
setMaxRetries(taskId: string, maxRetries: number): void;
```

### Step 3: 更新 07-phase-4-8.md Phase 6 - 添加 R7.1

在 WorkerPool.ts 核心接口中添加：

```typescript
// R7.1: Worker 崩溃恢复
detectCrashedWorkers(): Worker[];
async recoverWorker(workerId: string): Promise<boolean>;
async restartWorker(workerId: string): Promise<Worker>;
```

### Step 4: 更新 03-verification.md - 同步文件名

| 旧文件名 | 新文件名 | 说明 |
|----------|----------|------|
| PrdParser.ts | 删除 | 不需要单独解析器 |
| DependencyGraph.ts | TaskDAG.ts | 统一命名 |
| TaskStatusManager.ts | 合并到 TaskManager.ts | 简化结构 |
| PriorityCalculator.ts | 合并到 TaskScheduler.ts | 简化结构 |
| WorkflowEngine.ts | MasterOrchestrator.ts | 更准确命名 |
| HeartbeatManager.ts | 合并到 StatusReporter.ts | 已有 startHeartbeat() |
| SessionPersistence.ts | StateManager.ts | 已有 saveState/loadState |

### Step 5: 更新 03-verification.md - 补充需求矩阵

添加缺失的需求：

```markdown
| R6.3 | 资源使用监控 | 新建 | `ResourceMonitor.ts` | `test-resource-monitor.ts` | 🔲 |
| R6.4 | 实时日志捕获 | 新建 | `ResourceMonitor.ts` | `test-resource-monitor.ts` | 🔲 |
```

---

## 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `07-phase-4-8.md` | 添加 TODO 7.3 (ResourceMonitor), 更新 WorkerPool 接口 |
| `05-phase-2-task.md` | 更新 TaskScheduler 接口添加重试方法 |
| `03-verification.md` | 同步文件名 + 补充 R6.3/R6.4 到矩阵 |
| `00-index.md` | 更新执行顺序说明（可选） |

---

## 验收标准

- [ ] R6.3 (资源监控) 有明确 TODO 和接口定义
- [ ] R6.4 (日志捕获) 有明确 TODO 和接口定义
- [ ] R7.1 (崩溃恢复) 在 WorkerPool.ts 有明确方法
- [ ] R7.2 (失败重试) 在 TaskScheduler.ts 有明确方法
- [ ] 03-verification.md 文件名与 Phase 计划一致
- [ ] 需求矩阵包含全部 27 项需求

---

## 快速导航

- [00-index.md](00-index.md) - 索引
- [03-verification.md](03-verification.md) - 需求追溯
- [05-phase-2-task.md](05-phase-2-task.md) - Phase 2
- [07-phase-4-8.md](07-phase-4-8.md) - Phase 4-8
