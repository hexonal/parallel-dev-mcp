# Agent SDK + Tmux 混合执行器计划

## 问题背景

按照 README.md 架构设计，ParallelDev 系统要求：
- 每个 Worker 运行在独立的 **tmux 会话**中
- 每个 Worker 有独立的 **git worktree**
- 通过 tmux 实现会话隔离、输出监控、故障恢复

**当前问题**：
- `TaskExecutor` - 通过 tmux 执行 `claude` CLI ✅
- `AgentExecutor` - 直接使用 Agent SDK，**绕过了 tmux** ❌

---

## 方案：创建 HybridExecutor

### 核心设计

```
┌─────────────────────────────────────────────────────────────┐
│                    HybridExecutor                            │
├─────────────────────────────────────────────────────────────┤
│  1. 在 Tmux 会话中启动 Node.js 子进程                        │
│  2. 子进程中运行 Agent SDK query()                           │
│  3. 实时输出流式消息到 stdout                                │
│  4. SessionMonitor 监控 tmux 输出                            │
│  5. 保留所有 tmux 隔离和监控优势                             │
│  6. 获得 Agent SDK 的 Hooks、流式处理等高级功能               │
└─────────────────────────────────────────────────────────────┘
```

### 执行流程

```
Master 调用 HybridExecutor.execute(task, worktreePath)
    │
    ▼
┌─────────────────────────────────────────┐
│  1. 生成任务脚本文件                      │
│     scripts/worker-task-{taskId}.ts      │
│     - 包含 Agent SDK query() 调用        │
│     - 输出 JSON 格式的流式消息            │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  2. 在 Tmux 会话中执行脚本               │
│     tmux send-keys "npx tsx script.ts"  │
│     - 工作目录: worktreePath            │
│     - 独立进程，tmux 管理               │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  3. SessionMonitor 监控输出              │
│     - 解析 Agent SDK 流式 JSON 消息      │
│     - 触发 completed/failed 事件        │
│     - 输出持久化在 tmux 历史缓冲区        │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  4. 返回 TaskResult                      │
│     - success: boolean                   │
│     - output: string                     │
│     - metadata: { usage, executor }      │
└─────────────────────────────────────────┘
```

---

## 文件修改清单

### 新建文件

| 文件 | 说明 |
|------|------|
| `src/parallel/worker/HybridExecutor.ts` | 混合执行器主类 |
| `src/parallel/worker/worker-runner.ts` | Worker 运行脚本模板 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/parallel/master/MasterOrchestrator.ts` | 使用 HybridExecutor 替代 TaskExecutor |
| `src/parallel/worker/index.ts` | 导出 HybridExecutor |
| `src/parallel/index.ts` | 导出 HybridExecutor |

---

## 实施步骤

### Phase 1: 创建 worker-runner.ts
1. 创建 Worker 运行脚本模板
2. 实现 Agent SDK query() 调用
3. 实现结构化 JSON 输出

### Phase 2: 创建 HybridExecutor.ts
1. 实现 generateWorkerScript() - 动态生成脚本
2. 实现 execute() - 在 tmux 中执行脚本
3. 实现 waitForCompletion() - 监控和解析输出
4. 实现 parseAgentMessage() - 解析 Agent SDK 消息

### Phase 3: 更新 SessionMonitor
1. 添加 Agent SDK JSON 消息解析
2. 添加新的完成/失败标记检测
3. 保持向后兼容（支持旧的 stream-json 格式）

### Phase 4: 集成到 MasterOrchestrator
1. 替换 TaskExecutor 为 HybridExecutor
2. 更新导出文件
3. 运行测试验证

### Phase 5: 清理和测试
1. 更新 E2E 测试
2. 添加 HybridExecutor 单元测试

---

## 关键文件路径

### 需要修改
- `src/parallel/master/MasterOrchestrator.ts` - 行 21, 221-226
- `src/parallel/tmux/SessionMonitor.ts` - 添加 JSON 消息解析
- `src/parallel/worker/index.ts` - 导出 HybridExecutor
- `src/parallel/index.ts` - 导出 HybridExecutor

### 需要新建
- `src/parallel/worker/HybridExecutor.ts` - 混合执行器
- `src/parallel/worker/worker-runner.ts` - 脚本模板

### 保留不变
- `src/parallel/worker/TaskExecutor.ts` - 保留作为备选
- `src/parallel/worker/AgentExecutor.ts` - 保留用于直接 SDK 调用
- `src/parallel/tmux/TmuxController.ts` - 无需修改

---

## 预期收益

| 特性 | TaskExecutor | AgentExecutor | HybridExecutor |
|------|-------------|---------------|----------------|
| Tmux 会话隔离 | ✅ | ❌ | ✅ |
| 输出持久化 | ✅ | ❌ | ✅ |
| 进程独立管理 | ✅ | ❌ | ✅ |
| Agent SDK 功能 | ❌ | ✅ | ✅ |
| Hooks 安全检查 | ❌ | ✅ | ✅ |
| 流式消息处理 | 部分 | ✅ | ✅ |
| 故障恢复 | ✅ | ❌ | ✅ |
