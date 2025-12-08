# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

对话的时候，始终使用的是中文
每次的计划需要放到 [plans](.claude/plans)

---

## 📦 项目概述

**项目名称**: ParallelDev - Claude Code 自动化并行开发系统

**核心目标**: 通过 git worktree + Claude Code + 智能任务调度，实现真正的自动化并行开发，将开发效率提升 3-10 倍。

**技术栈**:
- **语言**: TypeScript (主要)
- **基础架构**: 基于 Happy (happy-cli) 架构
- **任务管理**: 集成 claude-task-master
- **会话隔离**: git worktree
- **会话管理**: tmux
- **通信**: Socket.IO + RPC (复用 Happy)
- **AI**: Claude Code SDK

**核心设计文档**: 📄 `claudedocs/PARALLELDEV_ARCHITECTURE.md`

---

## 🎯 核心设计原则

### 1. YAGNI 原则（You Aren't Gonna Need It）
- ✅ 只实现当前需要的功能
- ❌ 不考虑向后兼容
- ❌ 不考虑移动端
- ❌ 不使用 Shell 脚本（复杂逻辑用 TypeScript）

### 2. 改造 Happy 而非从头开始
- ✅ 在 `happy-cli/src/parallel/` 新增模块
- ✅ 复用 Happy 的 Socket.IO + RPC + 加密 + Claude SDK
- ❌ 不修改 Happy 核心代码

### 3. 清晰的架构分层
```
Layer 1: Task Management      → 任务管理
Layer 2: Orchestration        → 编排控制
Layer 3: Execution            → 任务执行
Layer 4: Communication        → Master-Worker 通信
Layer 5: Quality Assurance    → 质量保证
Layer 6: Notification         → 通知报告
```

### 4. 事件驱动架构
- 使用事件驱动而非轮询
- Worker 完成任务时触发新任务分配
- 基于 Happy 的 Socket.IO，天然支持事件

---

## 🚨 严格开发规范 (2025最新标准)

### TypeScript 代码质量标准

#### 函数长度严格限制
**🔴 强制要求**：
- **所有函数**: 不得超过50行（包含注释和空行）
- **超长处理**: 必须拆分为多个私有函数或使用设计模式
- **设计模式**: 优先使用工厂模式、策略模式、依赖注入
- **注释规范**:
  - 禁止使用行尾注释，所有注释必须独立成行
  - 每个函数必须有 JSDoc 注释
  - 复杂逻辑必须有步骤注释（如 `// 1. 初始化参数`）

#### 代码质量强制要求
- **类型安全**: 严格使用 TypeScript 类型，禁止 `any`
- **命名规范**:
  - 接口: `PascalCase`（如 `Task`, `Worker`）
  - 函数: `camelCase`（如 `assignTask`, `resolveConflicts`）
  - 常量: `UPPER_SNAKE_CASE`（如 `MAX_WORKERS`）
- **导入规范**: 使用 `@/` 别名，如 `import { logger } from '@/ui/logger'`
- **错误处理**:
  - 使用 `try-catch` 包裹可能失败的操作
  - 错误必须有清晰的错误消息
  - 关键操作失败时必须通知用户

### 禁用功能清单
**❌ 明确禁止**：
- **行尾注释**: 所有注释必须独立成行
- **深度嵌套**: 避免过度嵌套的数据结构（最多 3 层）
- **过度设计模式**: 避免为了模式而模式，保持简洁
- **`any` 类型**: 必须使用具体类型或 `unknown`
- **未处理的 Promise**: 所有 Promise 必须 `await` 或 `.catch()`

---

## 🏗️ ParallelDev 特定规范

### 1. 模块组织

```
happy-cli/src/parallel/
├── master/              # Master 控制层
│   ├── MasterOrchestrator.ts
│   ├── TaskScheduler.ts
│   ├── WorkerPool.ts
│   └── StateManager.ts
├── worker/              # Worker 执行层
│   ├── WorkerAgent.ts
│   ├── TaskExecutor.ts
│   └── StatusReporter.ts
├── git/                 # Git 集成
│   ├── WorktreeManager.ts
│   ├── ConflictResolver.ts
│   └── CodeValidator.ts
├── tmux/                # Tmux 管理
│   ├── TmuxController.ts
│   ├── SessionMonitor.ts
│   └── OutputCapture.ts
├── task/                # 任务管理
│   ├── TaskDAG.ts
│   ├── TaskMasterAdapter.ts
│   └── TaskValidator.ts
├── notification/        # 通知系统
│   ├── NotificationManager.ts
│   └── ReportGenerator.ts
└── index.ts             # 主入口
```

### 2. 核心数据结构

遵循 `claudedocs/PARALLELDEV_ARCHITECTURE.md` 中定义的数据结构：
- `Task`: 任务定义
- `Worker`: Worker 状态
- `Worktree`: Git worktree 信息
- `MasterMessage` / `WorkerMessage`: 通信协议

### 3. 文件命名规范

- **管理器类**: `*Manager.ts`（如 `WorktreeManager.ts`）
- **控制器类**: `*Controller.ts`（如 `TmuxController.ts`）
- **执行器类**: `*Executor.ts`（如 `TaskExecutor.ts`）
- **适配器类**: `*Adapter.ts`（如 `TaskMasterAdapter.ts`）
- **工具类**: `*Utils.ts`（如 `GitUtils.ts`）

### 4. 函数命名规范

- **创建操作**: `create*`（如 `createWorker`）
- **启动操作**: `start*`（如 `startMonitoring`）
- **停止操作**: `stop*`（如 `stopWorker`）
- **分配操作**: `assign*`（如 `assignTask`）
- **处理事件**: `on*` 或 `handle*`（如 `onTaskCompleted`, `handleWorkerFailure`）
- **检查状态**: `is*` 或 `check*`（如 `isWorkerHealthy`, `checkConflicts`）

### 5. 错误处理规范

```typescript
// ✅ 正确：详细的错误处理
async function assignTask(worker: Worker, task: Task) {
  try {
    // 1. 创建 worktree
    const worktree = await worktreeManager.create(task);

    // 2. 启动 tmux 会话
    const tmuxSession = await tmuxController.createSession({
      name: `parallel-dev-${worker.id}`,
      workingDir: worktree.path
    });

    // 3. 发送任务
    await sendTaskToWorker(worker, task, tmuxSession);

  } catch (error) {
    console.error(`❌ 分配任务失败: ${task.id}`, error);

    // 清理资源
    await cleanupFailedTask(worker, task);

    // 通知 Master
    await notificationManager.notify({
      type: 'task_assignment_failed',
      taskId: task.id,
      workerId: worker.id,
      error: error.message
    });

    throw error;
  }
}

// ❌ 错误：没有错误处理
async function assignTask(worker: Worker, task: Task) {
  const worktree = await worktreeManager.create(task);
  const tmuxSession = await tmuxController.createSession(...);
  await sendTaskToWorker(worker, task, tmuxSession);
}
```

### 6. 日志规范

```typescript
// 使用清晰的 emoji 和级别标识
console.log('✅ 任务完成:', taskId);
console.warn('⚠️  冲突检测到:', conflicts.length);
console.error('❌ Worker 崩溃:', workerId);
console.info('📦 分配任务:', taskId, '→', workerId);
console.debug('🔍 调试信息:', details);
```

### 7. 配置管理

所有配置必须有默认值：
```typescript
const DEFAULT_CONFIG: ParallelDevConfig = {
  concurrency: {
    maxWorkers: 3,
    autoScale: false
  },
  git: {
    mainBranch: 'main',
    worktreeDir: '.worktrees',
    autoCleanup: true,
    conflictStrategy: 'ai-assisted'
  },
  tmux: {
    sessionPrefix: 'parallel-dev',
    captureInterval: 15,
    logOutput: true
  },
  // ... 其他配置
};
```

---

## 🔧 MCP工具集成

项目集成了以下MCP工具以提供增强功能：

### 核心工具（必须使用）
- **sequential-thinking**: 复杂问题分析和决策支持（架构设计、问题诊断）
- **context7**: 技术文档和API查询（查询 Happy、Claude Code 等文档）
- **git-config**: Git仓库配置管理（检查 git 状态）
- **mcp-datetime**: 时间戳生成（日志、报告）

### 可选工具（按需使用）
- **deepwiki**: 深度技术知识查询
- **yapi-auto-mcp**: API文档自动化

### 使用建议
- 架构设计和复杂分析：使用 **sequential-thinking**
- 查询技术文档：使用 **context7** 或 **deepwiki**
- Git 操作前检查：使用 **git-config**

---

## 📝 开发检查清单

在提交代码前，确保：

### 代码质量
- [ ] 所有函数不超过 50 行
- [ ] 所有函数有 JSDoc 注释
- [ ] 复杂逻辑有步骤注释
- [ ] 没有 `any` 类型
- [ ] 没有行尾注释

### 架构符合性
- [ ] 遵循 6 层架构设计
- [ ] 使用事件驱动而非轮询
- [ ] 复用 Happy 的基础设施
- [ ] 没有修改 Happy 核心代码

### 错误处理
- [ ] 所有异步操作有 try-catch
- [ ] 错误有清晰的消息
- [ ] 失败时有资源清理
- [ ] 关键失败有通知

### 测试
- [ ] 单元测试覆盖核心逻辑
- [ ] 测试用例有清晰的描述
- [ ] 测试覆盖成功和失败场景

### 文档
- [ ] 新增功能更新架构文档
- [ ] 复杂逻辑有设计说明
- [ ] 公共 API 有使用示例

---

## 🚀 快速开始

### 开发新功能

1. **阅读架构文档**: 查看 `claudedocs/PARALLELDEV_ARCHITECTURE.md`
2. **确定所属层**: 确定功能属于哪个架构层
3. **创建模块**: 在对应目录创建文件
4. **编写代码**: 遵循上述规范
5. **编写测试**: 至少 80% 覆盖率
6. **更新文档**: 更新架构文档（如需要）

### 示例工作流

```bash
# 1. 创建新功能分支
git checkout -b feature/add-conflict-resolver

# 2. 开发功能（在 happy-cli/src/parallel/git/ 目录）
# 编写 ConflictResolver.ts

# 3. 编写测试
# 编写 ConflictResolver.test.ts

# 4. 运行测试
npm test

# 5. 检查代码质量
npm run lint
npm run typecheck

# 6. 提交代码
git add .
git commit -m "feat(git): 实现 ConflictResolver 分层冲突解决"

# 7. 推送并创建 PR
git push origin feature/add-conflict-resolver
```

---

## 📚 参考资料

- **架构设计**: `claudedocs/PARALLELDEV_ARCHITECTURE.md`
- **Happy 架构**: `happy-cli/CLAUDE.md`
- **Happy 代码**: `happy-cli/src/`
- **claude-task-master**: https://github.com/eyaltoledano/claude-task-master
- **Git Worktree 最佳实践**: 已通过 WebSearch 获取（2025 标准）
- **Tmux 自动化**: 已通过 WebSearch 获取（2025 标准）

---

## ⚠️ 重要提示

1. **始终使用中文对话**
2. **严格遵循架构文档**：所有设计决策必须与 `claudedocs/PARALLELDEV_ARCHITECTURE.md` 一致
3. **复用 Happy 基础设施**：不要重复实现 Socket.IO、RPC、加密等功能
4. **YAGNI 原则**：不要实现当前不需要的功能
5. **质量第一**：代码质量 > 开发速度
6. **测试优先**：关键功能必须有测试

---

**最后更新**: 2025-10-15
**项目状态**: 架构设计完成，准备开始 Phase 1 实施


