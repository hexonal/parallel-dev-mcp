# Phase -1/0/1：准备 + 基础设施 + Plugin

> 本文件包含 ParallelDev 重建的前三个阶段实施细节

---

## TODO 完成规范

> **🔴 重要**：每个 TODO 小点完成后，执行以下流程：
> 1. 使用 task agent 进行自测验证
> 2. 询问用户是否提交推送代码
> 3. 如用户同意，执行 `git add -A && git commit && git push`

---

## Phase -1: 分支准备

### TODO -1.1: 检查当前分支状态
```bash
git status
git branch
```
**完成后**：task agent 自测 → 询问是否提交推送

### TODO -1.2: 提交当前清空状态
```bash
git add -A
git commit -m "chore: 清空项目，准备从零重建"
git push origin feature/happy
```

---

## Phase 0: Pull 代码（核心前置）

**目标**：从外部仓库 Pull 代码，为后续爆改做准备

### TODO 0.1: Clone task-master 仓库到当前目录

**步骤**：
```bash
# 0.1.1 执行 clone
git clone https://github.com/eyaltoledano/claude-task-master.git ./claude-task-master

# 0.1.2 验证 clone 成功
ls -la ./claude-task-master
# 期望输出：应该看到 package.json, src/, etc.

# 0.1.3 检查源码目录结构
ls -la ./claude-task-master/src/ 2>/dev/null || ls -la ./claude-task-master/packages/
```
**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.2: 分析 task-master 源码结构

**步骤**：
```bash
# 0.2.1 查找所有 TypeScript 文件
find ./claude-task-master -name "*.ts" -type f | head -50

# 0.2.2 查找任务相关文件
find ./claude-task-master -name "*task*" -o -name "*Task*" | grep -E "\\.ts$"

# 0.2.3 查找 DAG 相关文件
find ./claude-task-master -name "*dag*" -o -name "*DAG*" -o -name "*dependency*" | grep -E "\\.ts$"

# 0.2.4 查找调度器相关文件
find ./claude-task-master -name "*scheduler*" -o -name "*Scheduler*" | grep -E "\\.ts$"
```

**记录需要参考的文件列表**（✅ 已完成探索）：

| 组件 | 源文件路径 | 行数 | 核心功能 |
|------|----------|------|----------|
| 循环依赖检测 | `dependency-manager.js:379-429` | 50 | `isCircularDependency()` |
| 依赖验证 | `dependency-manager.js:436-527` | 90 | `validateTaskDependencies()` |
| 下一个任务算法 | `task-service.ts:299-418` | 120 | `getNextTask()` |
| Task 类型定义 | `common/types/index.ts` | - | Task, TaskStatus, TaskPriority |
| tasks.json 格式 | `.taskmaster/tasks/tasks.json.example` | - | 任务文件格式 |

**⚠️ 重要发现**：
- task-master **没有独立的 TaskDAG 类**，依赖管理在 `dependency-manager.js` 中
- `modules/dependencies/` 是占位符（TODO: Migrate from scripts/modules/）
- 需要从 JS 代码提取并转换为 TypeScript

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.3: 爆改 task-master 核心代码到 TaskDAG.ts

**目标**：从 `dependency-manager.js` 提取核心逻辑，转换为 TypeScript

**爆改来源**：`./claude-task-master/scripts/modules/dependency-manager.js`

**核心代码片段（直接可用）**：

```javascript
// 1. 循环依赖检测 (lines 379-429)
function isCircularDependency(tasks, taskId, chain = []) {
  const taskIdStr = String(taskId);
  if (chain.some((id) => String(id) === taskIdStr)) {
    return true; // 发现循环
  }
  const newChain = [...chain, taskIdStr];
  return task.dependencies.some((depId) =>
    isCircularDependency(tasks, normalizedDepId, newChain)
  );
}

// 2. 依赖验证 (lines 436-527)
function validateTaskDependencies(tasks) {
  const issues = [];
  // 检查 self-dependencies, missing dependencies, circular dependencies
  return { valid: issues.length === 0, issues };
}
```

**改造步骤**：
```bash
# 0.3.1 创建/更新 TaskDAG.ts
# 将上述 JS 代码转换为 TypeScript 类方法

# 0.3.2 需要实现的方法：
# - detectCycle(taskId: string): boolean  ← 基于 isCircularDependency()
# - validateDependencies(): ValidationResult  ← 基于 validateTaskDependencies()
# - fixDependencies(): FixResult  ← 基于 fixDependenciesCommand()

# 0.3.3 验证
npx tsc --noEmit
```

**目标文件**：`src/parallel/task/TaskDAG.ts`

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.3b: 爆改 task-master 核心代码到 TaskScheduler.ts

**目标**：从 `task-service.ts` 提取下一个任务算法

**爆改来源**：`./claude-task-master/packages/tm-core/src/modules/tasks/services/task-service.ts:299-418`

**核心代码片段（直接可用）**：

```typescript
// 下一个任务算法
async getNextTask(tag?: string): Promise<Task | null> {
  const priorityValues = { critical: 4, high: 3, medium: 2, low: 1 };

  // 1. 从 in-progress 任务的子任务中查找
  // 2. 按 priority → dependencies → taskId 排序
  candidateSubtasks.sort((a, b) => {
    const pa = priorityValues[a.priority] ?? 2;
    const pb = priorityValues[b.priority] ?? 2;
    if (pb !== pa) return pb - pa;
    return a.dependencies.length - b.dependencies.length;
  });

  // 3. 回退到顶级任务
}
```

**改造步骤**：
```bash
# 0.3b.1 更新 TaskScheduler.ts
# 替换现有的 getNextTask 方法，使用 task-master 的算法

# 0.3b.2 新增批量获取方法
# getParallelTasks(count: number): Promise<Task[]>

# 0.3b.3 验证
npx tsc --noEmit
```

**目标文件**：`src/parallel/task/TaskScheduler.ts`

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.4: 爆改 Happy Socket.IO 客户端代码

**目标**：基于 `apiSocket.ts` 创建 Worker 客户端（无加密）

**爆改来源**：`./happy/sources/sync/apiSocket.ts`

**步骤**：
```bash
# 0.4.1 创建目标目录
mkdir -p src/parallel/communication

# 0.4.2 复制源文件
cp happy/sources/sync/apiSocket.ts src/parallel/communication/SocketClient.ts
```

**关键改动**（用户确认：不需要加密）：

```typescript
// 原始：面向用户会话
async sessionRPC<R, A>(sessionId: string, method: string, params: A)
async machineRPC<R, A>(machineId: string, method: string, params: A)

// 爆改：面向 Worker（移除加密）
async workerRPC<R, A>(method: string, params: A): Promise<R> {
  // 直接发送，无加密
  return this.socket.emitWithAck('rpc', { method, params });
}

async masterRPC<R, A>(method: string, params: A): Promise<R> {
  return this.socket.emitWithAck('rpc', { method, params });
}
```

**需要移除的代码**：
- ❌ `import { encrypt, decrypt } from '...'`
- ❌ `TokenStorage` 认证相关
- ❌ `getSessionEncryption()` / `getMachineEncryption()`
- ❌ 所有加密/解密逻辑

**目标文件**：`src/parallel/communication/SocketClient.ts`

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.5: 爆改 RPC 管理器代码

**目标**：基于 `RpcHandlerManager.ts` 创建简化版 RPC 管理器

**爆改来源**：`./happy-cli/src/api/rpc/RpcHandlerManager.ts`

**步骤**：
```bash
# 0.5.1 创建目录
mkdir -p src/parallel/communication/rpc

# 0.5.2 复制文件
cp happy-cli/src/api/rpc/RpcHandlerManager.ts src/parallel/communication/rpc/RpcManager.ts
cp happy-cli/src/api/rpc/types.ts src/parallel/communication/rpc/types.ts
```

**关键改动**：

```typescript
// 原始：会话级作用域
scopePrefix: sessionId | machineId

// 爆改：Worker 级作用域
scopePrefix: workerId

// 原始：加密密钥来自认证
getSessionEncryption(sessionId)

// 爆改：移除加密（用户确认不需要）
// 直接处理明文消息
```

**需要移除的代码**：
- ❌ 加密/解密逻辑
- ❌ 复杂的认证流程
- ❌ TokenStorage 相关

**目标文件**：`src/parallel/communication/rpc/RpcManager.ts`

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.6: 新建 SocketServer（Master 服务器）

**目标**：基于 Happy 模式新建 Master Socket 服务器

**步骤**：创建 `src/parallel/communication/SocketServer.ts`

**核心实现**：

```typescript
import { Server, Socket } from 'socket.io';
import { MasterCommand, WorkerEvent } from '../types';

export class MasterSocketServer {
  private io: Server;
  private workers: Map<string, Socket> = new Map();

  start(port: number): void {
    this.io = new Server(port);
    this.io.on('connection', (socket) => {
      const workerId = socket.handshake.query.workerId as string;
      this.workers.set(workerId, socket);

      socket.on('worker_event', (event: WorkerEvent) => {
        this.emit('worker_event', event);
      });

      socket.on('disconnect', () => {
        this.workers.delete(workerId);
      });
    });
  }

  async sendCommand(workerId: string, cmd: MasterCommand): Promise<void> {
    const socket = this.workers.get(workerId);
    if (socket) {
      await socket.emitWithAck('master_command', cmd);
    }
  }

  broadcast(event: string, data: unknown): void {
    this.io.emit(event, data);
  }
}
```

**目标文件**：`src/parallel/communication/SocketServer.ts`

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.7: 代码迁移（如需要）

**目标**：整合代码到统一目录结构

**步骤**：
```bash
# 0.7.1 确保目录结构正确
# 0.7.2 更新 package.json（合并依赖）
# 0.7.3 验证编译
npx tsc --noEmit
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.8: CLI 集成

**目标**：添加 `parallel` 子命令

**步骤**：

1. 新建 CLI 入口文件
2. 实现基础命令：
```typescript
// happy parallel --tasks tasks.json --concurrency 3
// happy parallel status
// happy parallel cancel --task-id task-1
// happy parallel report
```

**完成后**：task agent 自测 → 询问是否提交推送

---

**Phase 0 验收标准**：
- [ ] `./claude-task-master` 目录存在且包含源码
- [ ] `src/parallel/task/TaskDAG.ts` 包含爆改的循环检测逻辑
- [ ] `src/parallel/task/TaskScheduler.ts` 包含爆改的下一个任务算法
- [ ] `src/parallel/communication/SocketClient.ts` 爆改自 Happy（无加密）
- [ ] `src/parallel/communication/SocketServer.ts` 新建完成
- [ ] `src/parallel/communication/rpc/RpcManager.ts` 爆改自 Happy（无加密）
- [ ] CLI 命令可用
- [ ] TypeScript 编译通过（npx tsc --noEmit）

---

## Phase 1: 基础设施 + Claude Code Plugin

**目标**：建立项目骨架、核心类型、Plugin 架构

### TODO 1.1: 恢复项目基础配置

**步骤**：
```bash
# 1.1.1 创建 package.json
# 1.1.2 创建 tsconfig.json
# 1.1.3 创建 .gitignore
# 1.1.4 创建 vitest.config.ts
# 1.1.5 运行 yarn install 验证
```

**完成后**：task agent 自测（yarn install && yarn typecheck）→ 询问是否提交推送

### TODO 1.2: 创建核心类型定义 types.ts

**步骤**：
```bash
# 1.2.1 创建目录
mkdir -p src/parallel

# 1.2.2 创建 types.ts 文件
# 1.2.3 运行 tsc --noEmit 验证类型
```

**完成后**：task agent 自测（tsc --noEmit）→ 询问是否提交推送

### TODO 1.3: 创建 config.ts

**完成后**：task agent 自测（tsc --noEmit）→ 询问是否提交推送

### TODO 1.4: 创建 index.ts

**完成后**：task agent 自测（tsc --noEmit）→ 询问是否提交推送

### TODO 1.5: 创建运行状态目录模板

**步骤**：
```bash
# 1.5.1 创建 .paralleldev 目录
mkdir -p .paralleldev

# 1.5.2 创建 state.json 模板
# 1.5.3 创建 config.json 模板
# 1.5.4 创建 .taskmaster/tasks 目录
mkdir -p .taskmaster/tasks
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.6: 创建 Plugin 基础结构

**步骤**：
```bash
# 1.6.1 创建目录结构
mkdir -p paralleldev-plugin/.claude-plugin
mkdir -p paralleldev-plugin/commands
mkdir -p paralleldev-plugin/agents
mkdir -p paralleldev-plugin/skills
mkdir -p paralleldev-plugin/hooks
mkdir -p paralleldev-plugin/scripts

# 1.6.2 创建 plugin.json
# 1.6.3 验证目录结构
tree paralleldev-plugin/
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.7: 创建 Plugin 斜杠命令（5个）

- `/pd:start` - 启动并行执行
- `/pd:status` - 查看状态
- `/pd:assign` - 手动分配任务
- `/pd:stop` - 停止执行
- `/pd:report` - 生成报告

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.8: 创建 Plugin Agents（4个）

- `task-orchestrator` - 任务编排专家
- `quality-gate` - 代码质量门禁
- `conflict-resolver` - Git 冲突解决专家
- `worker-monitor` - Worker 监控

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.9: 创建核心 Plugin Skills（3个）

- `parallel-executor` - 并行任务执行能力
- `conflict-resolution` - Git 冲突解决能力
- `quality-assurance` - 代码质量保证能力

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.10: 创建语言相关 Skills（4个）

- `frontend-development` - 前端开发规范
- `go-development` - Go 开发规范
- `java-development` - Java 开发规范
- `typescript-development` - TypeScript 开发规范

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.11: 创建 Plugin Hooks 和 MCP 配置

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.12: 创建 Plugin 支持脚本

- `master-start.sh` - 启动 Master
- `worker-start.sh` - 启动 Worker
- `cleanup.sh` - 清理资源
- `notify-change.sh` - 通知文件变更
- `task-completed.sh` - 通知任务完成

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.13: 配置项目 .claude/ 目录

**完成后**：task agent 自测 → 询问是否提交推送

---

**Phase 1 验收标准**：
- [ ] `src/parallel/types.ts` 包含完整类型定义
- [ ] `src/parallel/config.ts` 包含配置管理
- [ ] `.paralleldev/` 目录和模板文件存在
- [ ] `paralleldev-plugin/` 目录结构完整：
  - [ ] `.claude-plugin/plugin.json` 存在
  - [ ] `commands/` 包含 5 个命令文件
  - [ ] `agents/` 包含 4 个 Agent 文件
  - [ ] `skills/` 包含 7 个 Skill 目录
  - [ ] `hooks/hooks.json` 存在
  - [ ] `.mcp.json` 存在
  - [ ] `scripts/` 包含 5 个脚本
- [ ] TypeScript 编译无错误

---

## 快速导航

- ← [返回索引](00-index.md)
- → [Phase 2: Layer 1 任务管理](05-phase-2-task.md)
