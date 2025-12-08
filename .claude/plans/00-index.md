# ParallelDev 重建实施计划索引

> 本计划从 task-master 和 Happy 两个项目进行全栈爆改，构建 ParallelDev 并行开发系统

## 核心目标

- **自动化并行开发**：通过 git worktree + Claude Code + 智能任务调度实现 3-10 倍效率提升
- **全栈爆改**：从 task-master 和 Happy 爆改核心代码，无外部运行时依赖
- **满足 README.md 30 项需求**：100% 需求覆盖，验证驱动开发 ⭐ 含 R6.3/R6.4

---

## 计划文件索引

| 文件 | 内容 | 状态 |
|------|------|------|
| [01-preparation.md](01-preparation.md) | Phase -1/0：准备 + Pull 代码 + 源码分析 | 完成 |
| [02-design.md](02-design.md) | Phase 0a/0b：爆改设计方案（task-master + 通信层） | 完成 |
| [03-verification.md](03-verification.md) | 验证策略 + README 需求追溯（30项） | ⭐ 已更新 |
| [04-phase-1-infra.md](04-phase-1-infra.md) | Phase 1：基础设施 + Plugin | 完成 |
| [05-phase-2-task.md](05-phase-2-task.md) | Phase 2：Layer 1 任务管理 + R7.2 重试 | ⭐ 已更新 |
| [06-phase-3-exec.md](06-phase-3-exec.md) | Phase 3：Layer 3 执行层 | 完成 |
| [07-phase-4-8.md](07-phase-4-8.md) | Phase 4-8：通信/质量/编排/通知/集成 | ⭐ 已更新 |
| [08-gap-fix.md](08-gap-fix.md) | 完整性修复方案（R6.3/R6.4/R7.1/R7.2） | ⭐ 新增 |

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        ParallelDev 系统                          │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Task Management    ← task-master 爆改                   │
│  Layer 2: Orchestration      ← task-master + 新建                 │
│  Layer 3: Execution          ← 新建（Worktree + Tmux + Claude）    │
│  Layer 4: Communication      ← Happy 爆改（Socket.IO + RPC）       │
│  Layer 5: Quality Assurance  ← 新建（冲突解决 + 质量门禁）           │
│  Layer 6: Notification       ← 新建（监控 + 报告）                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 爆改来源摘要

### task-master 爆改文件
| 源文件 | 目标文件 | 满足需求 |
|--------|----------|----------|
| `dependency-manager.js` | `TaskDAG.ts` | R1.2, R1.3 |
| `next-task.js` | `TaskScheduler.ts` | R1.4 |
| `workflow-orchestrator.ts` | `WorkerOrchestrator.ts` | R2.2 |
| `direct-functions/*.js` | `TaskManager.ts` | R1.1 |

### Happy 爆改文件

> **爆改目标**：在保留加密的基础上，实现 **父子进程双向 RPC 调用**

| 源文件 | 目标文件 | 爆改内容 | 满足需求 |
|--------|----------|----------|----------|
| `apiSocket.ts` | `SocketClient.ts` | 添加双向 RPC、请求-响应匹配 | R4.1, R4.2, R4.3 |
| `RpcHandlerManager.ts` | `RpcManager.ts` | 添加父→子调用、子→父回复 | R4.1 |

---

## 验证策略摘要

1. **单元验证**：每个爆改文件完成后运行对应测试脚本
2. **模块验证**：每层完成后运行端到端测试
3. **需求追溯**：30 项需求 100% 满足矩阵

验收标准：
- 完整需求满足矩阵所有行状态为 ✅
- 所有验证脚本通过
- 系统端到端测试通过

---

## 执行顺序

```
Phase -1: 分支准备                              ← 01-preparation.md
Phase 0:  Pull 代码 + 源码分析                   ← 01-preparation.md
Phase 0a: Task Master 爆改设计                  ← 02-design.md
Phase 0b: 通信层爆改设计                        ← 02-design.md
Phase 1:  基础设施 + Claude Code Plugin         ← 04-phase-1-infra.md ✅ 已完成
Phase 2:  Layer 1 任务管理（爆改 task-master）   ← 05-phase-2-task.md ✅ 已完成
Phase 3:  Layer 3 执行层（Tmux + Worktree）     ← 06-phase-3-exec.md ✅ 已完成
Phase 4:  Layer 4 通信层（Socket.IO + RPC）     ← 07-phase-4-8.md ✅ 已完成
Phase 5:  Layer 5 质量保证层                    ← 07-phase-4-8.md ✅ 已完成
Phase 6:  Layer 2 编排层                        ← 07-phase-4-8.md ✅ 已完成
Phase 7:  Layer 6 通知层                        ← 07-phase-4-8.md ✅ 已完成（含 R6.3/R6.4 ResourceMonitor）
Phase 8:  集成测试 + CLI                        ← 07-phase-4-8.md ✅ CLI 完成
```

---

## TODO 完成规范

> **重要**：每个 TODO 小点完成后，执行以下流程：
> 1. 使用 task agent 进行自测验证
> 2. 询问用户是否提交推送代码
> 3. 如用户同意，执行 `git add -A && git commit && git push`

---

## 快速导航

- 想了解准备工作？→ [01-preparation.md](01-preparation.md)
- 想了解爆改方案？→ [02-design.md](02-design.md)
- 想了解验证策略？→ [03-verification.md](03-verification.md)
- 想开始实施？→ [04-phase-1-infra.md](04-phase-1-infra.md)
