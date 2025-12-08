# 验证策略 + README 需求追溯

> 返回 [索引](00-index.md) | 上一篇: [爆改设计方案](02-design.md)

> **核心目标**：确保爆改的 Happy 和 task-master 组件完整满足 README.md 定义的所有功能需求

---

## 1. 需求清单（从 README.md 提取）

### Layer 1: Task Management（任务管理层）

| ID | 需求描述 | README 来源 |
|----|----------|-------------|
| R1.1 | 集成 claude-task-master 精细化任务管理 | 核心价值-解决痛点 |
| R1.2 | 任务依赖分析 - 构建任务依赖有向无环图（DAG） | 核心特性-智能任务调度 |
| R1.3 | 并行度识别 - 智能识别可并行执行的任务集合 | 核心特性-智能任务调度 |
| R1.4 | 动态任务分配 - Worker 空闲时自动分配下一个可执行任务 | 核心特性-智能任务调度 |
| R1.5 | 优先级支持 - 紧急任务优先执行 | 核心特性-智能任务调度 |

### Layer 2: Orchestration（编排控制层）

| ID | 需求描述 | README 来源 |
|----|----------|-------------|
| R2.1 | Master Orchestrator 主控制器 | 系统架构图 |
| R2.2 | 任务调度 | 系统架构-Layer 2 |
| R2.3 | Worker 管理（创建、监控、销毁） | 系统架构-Layer 2 |
| R2.4 | 状态监控 | 系统架构-Layer 2 |

### Layer 3: Execution（执行层）

| ID | 需求描述 | README 来源 |
|----|----------|-------------|
| R3.1 | Worker 运行在独立 worktree 中 | 核心设计原则-Git Worktree |
| R3.2 | 每个 Worker 有独立 Tmux 会话 | 系统架构图 |
| R3.3 | Worker 运行 Claude Code 执行任务 | 系统架构图 |

### Layer 4: Communication（通信层）

| ID | 需求描述 | README 来源 |
|----|----------|-------------|
| R4.1 | Master-Worker 通信 (Socket.IO + RPC) | 系统架构图 |
| R4.2 | 事件驱动架构 | 核心设计原则 |
| R4.3 | Worker 完成任务时触发新任务分配 | 工作流程-阶段2 |

### Layer 5: Quality Assurance（质量保证层）

| ID | 需求描述 | README 来源 |
|----|----------|-------------|
| R5.1 | 分层冲突解决（Level 1-3，>70% 自动解决） | 核心特性-分层冲突解决 |
| R5.2 | 自动测试 - Worker 完成任务后自动运行测试 | 核心特性-全面质量保证 |
| R5.3 | Lint 检查 - ESLint/TSLint | 核心特性-全面质量保证 |
| R5.4 | 类型检查 - TypeScript | 核心特性-全面质量保证 |
| R5.5 | 质量门禁 - 所有检查通过才允许合并 | 核心特性-全面质量保证 |

### Layer 6: Notification（通知报告层）

| ID | 需求描述 | README 来源 |
|----|----------|-------------|
| R6.1 | 实时监控 Worker 状态（空闲/忙碌/错误） | 核心特性-实时监控 |
| R6.2 | 任务进度显示 | 核心特性-实时监控 |
| R6.3 | 资源使用监控 | 核心特性-实时监控 |
| R6.4 | 实时日志捕获 | 核心特性-实时监控 |
| R6.5 | 完成报告生成 | 工作流程-阶段4 |
| R6.6 | 通知发送（终端/声音/Web） | 工作流程-阶段4 |

### 可靠性需求

| ID | 需求描述 | README 来源 |
|----|----------|-------------|
| R7.1 | Worker 崩溃恢复 - 自动检测并重启 | 核心特性-错误恢复 |
| R7.2 | 任务失败重试 - 失败任务重新分配 | 核心特性-错误恢复 |
| R7.3 | 心跳机制 - 30 秒检测，>90 秒无响应标记失败 | 核心特性-错误恢复 |
| R7.4 | 会话持久化 - 支持中断恢复 | 核心特性-错误恢复 |

---

## 2. 爆改来源追溯

### task-master 爆改 → 满足需求

| task-master 源文件 | 爆改后文件 | 满足需求 |
|-------------------|------------|----------|
| `mcp/tools/parse_prd.ts` | `PrdParser.ts` | R1.1 |
| `mcp/tools/next_task.ts` + `direct-functions/next-task.js` | `TaskScheduler.ts` | R1.2, R1.3, R1.4 |
| `mcp/tools/set_task_status.ts` | `TaskStatusManager.ts` | R1.4 |
| `core/dependency-manager.js` | `DependencyGraph.ts` | R1.2, R1.3 |
| `mcp/tools/analyze_task_complexity.ts` | `PriorityCalculator.ts` | R1.5 |
| `core/workflow-orchestrator.ts` | `WorkflowEngine.ts` | R2.2 |

### Happy 爆改 → 满足需求

> **爆改目标**：在保留加密的基础上，实现 **父子进程双向 RPC 调用**

| Happy 源文件 | 目标文件 | 爆改内容 | 满足需求 |
|-------------|----------|----------|----------|
| `apiSocket.ts` | `SocketClient.ts` | 添加双向 RPC、请求-响应匹配 | R4.1, R4.2, R4.3 |
| `RpcHandlerManager.ts` | `RpcManager.ts` | 添加父→子调用、子→父回复 | R4.1 |

**爆改原因**：Happy 当前是单向 RPC，ParallelDev 需要双向 RPC（父子进程互调）

### 新建模块 → 满足需求

| 新建文件 | 满足需求 |
|----------|----------|
| `SocketServer.ts` | R4.1, R4.2 |
| `MasterOrchestrator.ts` | R2.1, R2.2, R2.3, R2.4 |
| `WorkerPool.ts` | R2.3, R7.1 |
| `TaskExecutor.ts` | R3.1, R3.2, R3.3 |
| `WorktreeManager.ts` | R3.1 |
| `TmuxController.ts` | R3.2, R6.4 |
| `ConflictResolver.ts` | R5.1 |
| `TestRunner.ts` | R5.2 |
| `LintChecker.ts` | R5.3 |
| `TypeChecker.ts` | R5.4 |
| `QualityGate.ts` | R5.5 |
| `StatusMonitor.ts` | R6.1, R6.2, R6.3 |
| `ReportGenerator.ts` | R6.5, R6.6 |
| `HeartbeatManager.ts` | R7.3 |
| `SessionPersistence.ts` | R7.4 |

---

## 3. 需求验证方法

### R1.x（任务管理）验证

| 需求 | 验证脚本 | 通过条件 |
|------|----------|----------|
| R1.1 | `test-prd-parser.ts` | PRD 成功解析为 Task 列表 |
| R1.2 | `test-dag-builder.ts` | 依赖图正确构建，无循环依赖 |
| R1.3 | `test-parallel-detection.ts` | 正确识别可并行任务集合 |
| R1.4 | `test-task-assignment.ts` | Worker 空闲时立即获得新任务 |
| R1.5 | `test-priority-queue.ts` | 高优先级任务优先执行 |

### R2.x（编排控制）验证

| 需求 | 验证场景 | 通过条件 |
|------|----------|----------|
| R2.1 | 启动 MasterOrchestrator | 成功初始化并进入主循环 |
| R2.2 | 提交任务列表 | 任务按依赖顺序分配 |
| R2.3 | 创建 3 个 Worker | WorkerPool 管理 3 个 Worker 实例 |
| R2.4 | 监控 Worker 状态 | StatusMonitor 实时更新状态 |

### R3.x（执行层）验证

| 需求 | 验证场景 | 通过条件 |
|------|----------|----------|
| R3.1 | 分配任务给 Worker | 创建独立 worktree |
| R3.2 | Worker 启动 | 创建 tmux 会话 |
| R3.3 | Worker 执行任务 | Claude Code 成功运行 |

### R4.x（通信层）验证

| 需求 | 验证脚本 | 通过条件 |
|------|----------|----------|
| R4.1 | `test-e2e-communication.ts` | Socket.IO + RPC 完整工作 |
| R4.2 | `test-e2e-communication.ts` | 事件正确触发和处理 |
| R4.3 | `test-e2e-communication.ts` | 任务完成事件触发新分配 |

### R5.x（质量保证）验证

| 需求 | 验证场景 | 通过条件 |
|------|----------|----------|
| R5.1 | 构造冲突场景 | Level 1/2 自动解决，Level 3 提示人工 |
| R5.2 | Worker 完成任务 | 自动运行 `npm test` |
| R5.3 | Worker 完成任务 | 自动运行 `eslint` |
| R5.4 | Worker 完成任务 | 自动运行 `tsc --noEmit` |
| R5.5 | 质量检查 | 任一检查失败则阻止合并 |

### R6.x（通知报告）验证

| 需求 | 验证场景 | 通过条件 |
|------|----------|----------|
| R6.1 | 运行系统 | 实时显示 Worker 状态 |
| R6.2 | 运行任务 | 显示任务进度百分比 |
| R6.5 | 所有任务完成 | 生成完整报告 |
| R6.6 | 所有任务完成 | 发送通知到终端 |

### R7.x（可靠性）验证

| 需求 | 验证场景 | 通过条件 |
|------|----------|----------|
| R7.1 | 杀死 Worker 进程 | 自动重启 Worker |
| R7.2 | 任务执行失败 | 任务重新分配给其他 Worker |
| R7.3 | Worker 无响应 | 90 秒后标记为失败 |
| R7.4 | 中断系统后恢复 | 从上次状态继续 |

---

## 4. 完整需求满足矩阵

> ⭐ 已同步文件名与 Phase 计划一致，补充 R6.3/R6.4

| 需求ID | 描述 | 来源组件 | 目标文件 | 验证脚本 | 状态 |
|--------|------|----------|----------|----------|------|
| R1.1 | 集成 task-master | task-master | `TaskManager.ts` | `test-task-manager.ts` | 🔲 |
| R1.2 | 任务依赖 DAG | task-master | `TaskDAG.ts` | `test-dag-builder.ts` | 🔲 |
| R1.3 | 并行度识别 | task-master | `TaskDAG.ts` | `test-parallel-detection.ts` | 🔲 |
| R1.4 | 动态任务分配 | task-master | `TaskScheduler.ts` | `test-task-assignment.ts` | 🔲 |
| R1.5 | 优先级支持 | task-master | `TaskScheduler.ts` | `test-priority-queue.ts` | 🔲 |
| R2.1 | Master 主控制器 | 新建 | `MasterOrchestrator.ts` | `test-master-orchestrator.ts` | 🔲 |
| R2.2 | 任务调度 | task-master | `MasterOrchestrator.ts` | `test-master-orchestrator.ts` | 🔲 |
| R2.3 | Worker 管理 | 新建 | `WorkerPool.ts` | `test-master-orchestrator.ts` | 🔲 |
| R2.4 | 状态监控 | 新建 | `StateManager.ts` | `test-state-manager.ts` | 🔲 |
| R3.1 | Worktree 隔离 | 新建 | `WorktreeManager.ts` | `test-worker-execution.ts` | 🔲 |
| R3.2 | Tmux 会话 | 新建 | `TmuxController.ts` | `test-worker-execution.ts` | 🔲 |
| R3.3 | Claude Code 执行 | 新建 | `TaskExecutor.ts` | `test-worker-execution.ts` | 🔲 |
| R4.1 | Socket.IO + RPC | Happy | `SocketClient.ts`, `SocketServer.ts` | `test-e2e-communication.ts` | 🔲 |
| R4.2 | 事件驱动 | Happy | `SocketServer.ts` | `test-e2e-communication.ts` | 🔲 |
| R4.3 | 任务完成触发 | Happy | `SocketServer.ts` | `test-e2e-communication.ts` | 🔲 |
| R5.1 | 分层冲突解决 | 新建 | `ConflictResolver.ts` | `test-conflict-resolver.ts` | 🔲 |
| R5.2 | 自动测试 | 新建 | `CodeValidator.ts` | `test-quality-gate.ts` | 🔲 |
| R5.3 | Lint 检查 | 新建 | `CodeValidator.ts` | `test-quality-gate.ts` | 🔲 |
| R5.4 | 类型检查 | 新建 | `CodeValidator.ts` | `test-quality-gate.ts` | 🔲 |
| R5.5 | 质量门禁 | 新建 | `SubagentRunner.ts` | `test-quality-gate.ts` | 🔲 |
| R6.1 | Worker 状态监控 | 新建 | `NotificationManager.ts` | `test-notification.ts` | 🔲 |
| R6.2 | 任务进度显示 | 新建 | `NotificationManager.ts` | `test-notification.ts` | 🔲 |
| R6.3 | 资源使用监控 | 新建 | `ResourceMonitor.ts` | `test-resource-monitor.ts` | 🔲 ⭐ |
| R6.4 | 实时日志捕获 | 新建 | `ResourceMonitor.ts` | `test-resource-monitor.ts` | 🔲 ⭐ |
| R6.5 | 完成报告 | 新建 | `ReportGenerator.ts` | `test-report-generator.ts` | 🔲 |
| R6.6 | 通知发送 | 新建 | `NotificationManager.ts` | `test-notification.ts` | 🔲 |
| R7.1 | Worker 崩溃恢复 | 新建 | `WorkerPool.ts` | `test-worker-recovery.ts` | 🔲 |
| R7.2 | 任务失败重试 | 新建 | `TaskScheduler.ts` | `test-task-retry.ts` | 🔲 |
| R7.3 | 心跳机制 | 新建 | `StatusReporter.ts` | `test-worker-recovery.ts` | 🔲 |
| R7.4 | 会话持久化 | 新建 | `StateManager.ts` | `test-session-recovery.ts` | 🔲 |

---

## 5. 验证执行计划

```
Phase 1: task-master 爆改验证（R1.x）
├── 1.1 爆改 dependency-manager.js → DependencyGraph.ts
├── 1.2 运行 test-dag-builder.ts → 验证 R1.2, R1.3
├── 1.3 爆改 next-task.js → TaskScheduler.ts
├── 1.4 运行 test-task-assignment.ts → 验证 R1.4
└── 1.5 通过标准：R1.1-R1.5 全部 ✅

Phase 2: Happy 爆改验证（R4.x）
├── 2.1 爆改 apiSocket.ts → SocketClient.ts（添加双向 RPC）
├── 2.2 爆改 RpcHandlerManager.ts → RpcManager.ts（添加父子互调）
├── 2.3 新建 SocketServer.ts（支持双向 RPC）
├── 2.4 运行 test-e2e-communication.ts → 验证 R4.1-R4.3
└── 2.5 通过标准：R4.1-R4.3 全部 ✅（保留加密 + 双向 RPC）

Phase 3: 执行层实现验证（R3.x）
├── 3.1 新建 WorktreeManager.ts
├── 3.2 新建 TmuxController.ts
├── 3.3 爆改 claudeSdk.ts → ClaudeExecutor.ts
├── 3.4 运行 test-worker-execution.ts → 验证 R3.1-R3.3
└── 3.5 通过标准：R3.1-R3.3 全部 ✅

Phase 4: 编排层实现验证（R2.x）
├── 4.1 新建 MasterOrchestrator.ts
├── 4.2 新建 WorkerPool.ts
├── 4.3 爆改 workflow-orchestrator.ts → WorkflowEngine.ts
├── 4.4 运行 test-master-orchestrator.ts → 验证 R2.1-R2.4
└── 4.5 通过标准：R2.1-R2.4 全部 ✅

Phase 5: 质量保证实现验证（R5.x）
├── 5.1 新建 ConflictResolver.ts, TestRunner.ts, LintChecker.ts, TypeChecker.ts, QualityGate.ts
├── 5.2 运行 test-quality-gate.ts → 验证 R5.1-R5.5
└── 5.3 通过标准：R5.1-R5.5 全部 ✅

Phase 6: 通知报告实现验证（R6.x）
├── 6.1 新建 NotificationManager.ts, ReportGenerator.ts, ResourceMonitor.ts ⭐
├── 6.2 运行 test-notification.ts, test-resource-monitor.ts → 验证 R6.1-R6.6
└── 6.3 通过标准：R6.1-R6.6 全部 ✅（含 R6.3/R6.4 资源监控和日志捕获）

Phase 7: 可靠性实现验证（R7.x）
├── 7.1 StatusReporter.ts(心跳), StateManager.ts(持久化), WorkerPool.ts(恢复), TaskScheduler.ts(重试) ⭐
├── 7.2 运行 test-worker-recovery.ts, test-session-recovery.ts → 验证 R7.1-R7.4
└── 7.3 通过标准：R7.1-R7.4 全部 ✅

最终验收：所有 30 项需求 ✅ → README.md 需求 100% 满足 ⭐ 修正（含 R6.3/R6.4）
```

---

## 6. 验收标准

- ✅ 完整需求满足矩阵所有行状态为 ✅
- ✅ 所有验证脚本通过
- ✅ 系统端到端测试通过
- ✅ 用户验收测试通过

---

> 下一步: [Phase 0-1 实施](04-phase-0-1.md)
