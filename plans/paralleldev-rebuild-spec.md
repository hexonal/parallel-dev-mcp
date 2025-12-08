# ParallelDev 从零重建方案

## 背景

清空现有 `src/parallel/` 目录（23 个文件，~7,318 行代码），基于 README.md 设计思路 + Claude Code 2025 新能力从零重建。

**核心目标**：
1. 严格遵循 README.md 的 6 层架构设计
2. 最大化利用 Claude Code 2025 新能力（Headless、Subagent、Skills）
3. **Pull Happy 的 Socket.IO + RPC 代码并爆改**（任务完成通知方式）
4. **Pull task-master.dev 源码并爆改**（不是自己实现）
5. 事件驱动，无轮询
6. YAGNI 原则，最小可用

---

## 🔀 Phase -1: 分支准备策略

### 基于当前分支工作

**当前分支**：`feature/happy`（继续使用）

### 清空策略

**🔴 完全清空 src/parallel/ 目录**，然后从 task-master 和 Happy Pull 代码重建。

```bash
# 完全删除 src/parallel/ 目录
rm -rf src/parallel/

# 重新创建空目录
mkdir -p src/parallel/
```

### 每步提交推送规则

**🔴 重要**：每个 TODO 完成后必须：
1. `git add -A`
2. `git commit -m "step description"`
3. `git push origin feature/happy`

### 分支准备 TODO

- [ ] **TODO -1.1**: 检查当前分支状态 (`git status`) → 提交推送
- [ ] **TODO -1.2**: 完全删除 src/parallel/ 目录 → 提交推送
- [ ] **TODO -1.3**: 修正 README.md → 提交推送

---

## 📝 README 修正计划

### 发现的问题

| 问题 | README 现状 | 修正方案 |
|-----|------------|---------|
| **目录结构错误** | `happy-cli/src/parallel/` | 改为 `src/parallel/` |
| **CLI 命令错误** | `happy parallel --tasks tasks.json` | 改为 `paralleldev run --tasks tasks.json` |
| **安装命令错误** | `cd happy-cli && yarn install` | 改为 `yarn install` |
| **构建命令错误** | `cd happy-cli && yarn build` | 改为 `yarn build` |
| **开发工作流路径** | `happy-cli/src/parallel/git/` | 改为 `src/parallel/git/` |
| **核心设计原则冲突** | "在 `happy-cli/src/parallel/` 新增模块" | 改为 "在 `src/parallel/` 新增模块" |
| **核心设计原则冲突** | "❌ 不修改 Happy 核心代码" | 添加说明："复制 Happy 代码并爆改，原 Happy 代码不变" |

### README 修正 TODO

- [ ] **TODO README.1**: 修正目录结构（所有 `happy-cli/src/parallel/` → `src/parallel/`）
- [ ] **TODO README.2**: 修正 CLI 命令（`happy parallel` → `paralleldev`）
- [ ] **TODO README.3**: 修正安装和构建命令
- [ ] **TODO README.4**: 修正开发工作流路径
- [ ] **TODO README.5**: 添加 "Pull 代码并爆改" 说明，澄清与 "不修改 Happy 核心代码" 的关系
- [ ] **TODO README.6**: 更新技术栈目录结构图

### README 修正后的关键内容

**安装命令**：
```bash
# 克隆仓库
git clone https://github.com/your-org/parallel-dev-mcp.git
cd parallel-dev-mcp

# 安装依赖
yarn install

# 构建项目
yarn build
```

**使用示例**：
```bash
# 1. 使用 claude-task-master 生成任务列表
taskmaster generate --from-prd prd.md --output .taskmaster/tasks/tasks.json

# 2. 启动 ParallelDev
paralleldev run --tasks .taskmaster/tasks/tasks.json --workers 3

# 3. 查看状态
paralleldev status

# 4. 生成报告
paralleldev report
```

**核心设计原则修正**：
```markdown
#### 1. 复用 Happy 通信架构
- ✅ **复制** Happy 的 Socket.IO + RPC 代码到 `src/parallel/communication/`
- ✅ 在复制的代码上进行**爆改**（简化加密、移除认证）
- ❌ **不直接修改** Happy 源码（`happy/` 目录保持不变）
```

---

## 🔍 冲突检查结果

### 已识别的冲突

| # | 冲突类型 | 描述 | 解决方案 |
|---|---------|------|---------|
| 1 | **目录结构** | README 说 `happy-cli/src/parallel/`，但实际是 `src/parallel/` | 修正 README |
| 2 | **CLI 命令** | README 说 `happy parallel`，计划说 `paralleldev` | 统一为 `paralleldev`，修正 README |
| 3 | **Happy 代码策略** | README 说 "❌ 不修改 Happy 核心代码"，计划说 "Pull 并爆改" | 不冲突：是"复制"并爆改，不是直接修改 |
| 4 | **任务配置路径** | README 提 `.taskmaster/tasks/tasks.json`，计划部分说 `.paralleldev/tasks.json` | 统一为 `.taskmaster/tasks/tasks.json`（保持兼容） |
| 5 | **删除 vs 保留** | 计划说"清空"，但部分文件需要保留 | 明确分类：保留/爆改/删除三类 |
| 6 | **Plugin 目录** | 计划说 `paralleldev-plugin/`，但项目根目录没有 | Phase 1 中创建 |

### 无冲突确认

| # | 项目 | 状态 |
|---|-----|------|
| 1 | 6 层架构设计 | README 和计划一致 ✅ |
| 2 | Socket.IO + RPC 通信 | README 和计划一致（都使用 Happy 风格）✅ |
| 3 | Tmux 会话管理 | README 和计划一致 ✅ |
| 4 | Git Worktree 隔离 | README 和计划一致 ✅ |
| 5 | 事件驱动架构 | README 和计划一致 ✅ |
| 6 | YAGNI 原则 | README 和计划一致 ✅ |

### 冲突解决后的统一标准

```
项目结构标准
────────────────────────────────────────────
代码目录:           src/parallel/
CLI 命令:           paralleldev
任务配置目录:        .taskmaster/tasks/
运行状态目录:        .paralleldev/
Plugin 目录:        paralleldev-plugin/

Happy 代码策略
────────────────────────────────────────────
原始目录:           happy/ (不修改)
复制到:            src/parallel/communication/
爆改内容:           移除加密、简化认证、适配 Master-Worker
```

---

## 🎯 小需求定义与验证机制

### 核心原则

**每个小需求（TODO）完成后，使用 Claude Task Agent 进行验证**

### 小需求总览（共 56+ 个）

| Phase | 小需求数量 | 验证方式 |
|-------|-----------|---------|
| **Phase -1** | **3 个 TODO** | **分支状态验证 + 提交推送** |
| **README 修正** | **在 Phase -1.3 中完成** | **文档审核** |
| Phase 0 | 6 个 TODO | 文件存在性验证 |
| Phase 1 | 17 个 TODO（含 4 个语言 Skills） | 结构验证 + Plugin 加载测试 |
| Phase 2 | 3 个 TODO | 单元测试 + 功能验证 |
| Phase 3 | 5 个 TODO | 端到端测试 |
| Phase 4 | 5 个 TODO | Socket 通信测试 |
| Phase 5 | 3 个 TODO | 集成测试 |
| Phase 6 | 3 个 TODO | 质量检查测试 |
| Phase 7 | 2 个 TODO | 通知功能测试 |
| Phase 8 | 3 个 TODO | 完整端到端测试 |

### 验证流程

```
┌─────────────────────────────────────────────────────────────┐
│                 小需求验证流程                               │
└─────────────────────────────────────────────────────────────┘

每个 TODO 完成后：
    │
    ├─ 1. 自动验证
    │   └─ 运行对应的单元测试/集成测试
    │
    ├─ 2. Claude Task Agent 验证
    │   └─ 使用 task-checker agent 验证实现是否符合规范
    │
    ├─ 3. 标记完成
    │   └─ 将 TODO 的 [ ] 改为 [x]
    │
    └─ 4. 进入下一个 TODO
        └─ 如果是 Phase 最后一个 TODO，执行 Phase 验收

每个 Phase 完成后：
    │
    ├─ 1. 运行 Phase 验证命令
    │   └─ claude task verify-phase --phase=N
    │
    ├─ 2. 检查所有验收标准
    │   └─ 所有 [ ] 变为 [x]
    │
    └─ 3. 生成 Phase 完成报告
        └─ 记录耗时、问题、解决方案
```

### Claude Task Agent 验证命令

```bash
# 验证单个 TODO
claude task verify-todo --todo="TODO 1.9.1" --check="files,structure"

# 验证整个 Phase
claude task verify-phase --phase=1 --run-tests --check-coverage

# 生成验证报告
claude task report --format=markdown --output=claudedocs/verification-report.md
```

### 关键验证点

1. **代码质量验证**：每个 TODO 完成后运行 `tsc --noEmit` 和 `eslint`
2. **测试覆盖验证**：确保新代码有对应的单元测试
3. **功能验证**：手动或自动验证功能正确性
4. **文档验证**：确保 JSDoc 注释完整

---

## 零、Pull 代码策略（核心）

### 🔴 关键原则：Pull 代码 → 爆改，而非从零实现

用户明确要求："我希望是 pull taskmaster 的代码，然后开始去爆改。而是不会简单的自己实现。Happy 风格通信 我希望的也是如此"

### 1. 从 task-master.dev GitHub 仓库 Pull

**仓库地址**：`https://github.com/eyaltoledano/claude-task-master`

**需要 Clone/Pull 的内容**：
```bash
# Clone 仓库到临时目录
git clone https://github.com/eyaltoledano/claude-task-master.git /tmp/claude-task-master

# 查看源码结构
ls -la /tmp/claude-task-master/packages/task-master-ai/src/
```

**需要复制的核心文件**：
| 源文件（task-master 仓库） | 目标位置 | 爆改内容 |
|---------------------------|---------|---------|
| `packages/*/src/*task*.ts` | `src/parallel/task/` | 简化复杂度，保留核心 |
| `packages/*/src/*dag*.ts` | `src/parallel/task/TaskDAG.ts` | 完全保留依赖图逻辑 |
| `packages/*/src/*scheduler*.ts` | `src/parallel/task/TaskScheduler.ts` | 简化调度策略 |
| `.taskmaster/tasks/tasks.json` 格式定义 | - | 保留格式 |

**爆改策略**：
- ✅ 保留：TaskDAG（依赖图 + 拓扑排序）
- ✅ 保留：tasks.json 格式（id, title, description, dependencies, priority, status）
- ⚡ 简化：TaskScheduler（仅保留 PRIORITY_FIRST + DEPENDENCY_FIRST）
- ❌ 移除：复杂的序列化逻辑
- ❌ 移除：多语言支持
- ❌ 移除：高级调度策略（LOAD_BALANCED）

### 2. 从 Happy 项目复制 Socket.IO 代码

**Happy 项目位置**：`/Users/flink/PycharmProjects/parallel-dev-mcp/happy/`

**需要复制的核心文件**：
| 源文件（Happy 项目） | 目标位置 | 爆改内容 |
|---------------------|---------|---------|
| `happy/sources/sync/apiSocket.ts` | `src/parallel/communication/SocketClient.ts` | 简化为 Worker 端 Socket 客户端 |
| `src/api/rpc/RpcHandlerManager.ts` | `src/parallel/communication/RpcManager.ts` | 简化加密，保留 RPC 模式 |
| `src/api/rpc/types.ts` | `src/parallel/communication/types.ts` | 保留核心类型 |

**Happy apiSocket.ts 核心功能**（262行）：
```typescript
// 需要保留的核心模式：
- io() Socket.IO 连接管理
- connect() / disconnect() 连接生命周期
- onMessage() / send() 消息收发
- emitWithAck() 带确认的消息
- sessionRPC() / machineRPC() RPC 调用模式
- setupEventHandlers() 事件处理设置
- onStatusChange() 连接状态监听
- onReconnected() 重连处理
```

**Happy RpcHandlerManager.ts 核心功能**（135行）：
```typescript
// 需要保留的核心模式：
- registerHandler() RPC 方法注册
- handleRequest() 请求处理
- onSocketConnect() / onSocketDisconnect() Socket 生命周期
- socket.emit('rpc-register') 注册 RPC 方法
- socket.emit('rpc-call') 调用 RPC
```

**爆改策略**：
- ✅ 保留：Socket.IO 连接管理
- ✅ 保留：emit / emitWithAck 消息模式
- ✅ 保留：RPC 注册和调用模式
- ⚡ 简化：移除加密（encrypt/decrypt）
- ⚡ 简化：移除 session/machine 区分
- ❌ 移除：TokenStorage 认证
- ❌ 移除：HTTP request 方法

### 3. 现有代码保留清单

**项目中已有的可直接爆改的文件**：
| 现有文件 | 策略 | 说明 |
|---------|------|------|
| `src/parallel/task/TaskDAG.ts` | ✅ 保留 | 已有依赖图实现 |
| `src/parallel/task/TaskMasterAdapter.ts` | ⚡ 爆改 | 重命名为 TaskManager |
| `src/parallel/task/TaskScheduler.ts` | ⚡ 简化 | 移除复杂策略 |
| `src/parallel/tmux/TmuxController.ts` | ✅ 保留 | 会话管理核心 |
| `src/parallel/tmux/SessionMonitor.ts` | ✅ 保留 | 输出监控 |
| `src/parallel/types.ts` | ⚡ 简化 | 保留核心类型 |

### 4. Pull + 爆改执行步骤

```bash
# Step 1: Clone task-master 仓库
git clone https://github.com/eyaltoledano/claude-task-master.git /tmp/claude-task-master

# Step 2: 分析源码结构
find /tmp/claude-task-master -name "*.ts" -path "*/src/*" | head -50

# Step 3: 复制核心文件到项目
# （具体文件在 Phase 2 实施时确定）

# Step 4: 复制 Happy Socket.IO 代码
cp happy/sources/sync/apiSocket.ts src/parallel/communication/SocketClient.ts
cp src/api/rpc/RpcHandlerManager.ts src/parallel/communication/RpcManager.ts
cp src/api/rpc/types.ts src/parallel/communication/types.ts

# Step 5: 爆改（简化 + 适配）
# - 移除加密逻辑
# - 移除认证逻辑
# - 适配 Worker/Master 通信模式
```

### 5. 爆改对照表

| 原始代码 | 爆改后 | 变化 |
|---------|-------|------|
| `apiSocket.ts` (262行) | `SocketClient.ts` (~150行) | -43% |
| `RpcHandlerManager.ts` (135行) | `RpcManager.ts` (~80行) | -41% |
| task-master TaskDAG | `TaskDAG.ts` | 完全保留 |
| task-master TaskScheduler | `TaskScheduler.ts` (~100行) | 简化策略 |
| `TaskMasterAdapter.ts` (168行) | `TaskManager.ts` (~100行) | -40% |

---

## 一、通信架构（参考 Happy 项目）

### 核心设计：Socket.IO + StatusReporter（非 Hook）

**参考 Happy 项目的实现**：
- 文件：`happy-cli/src/api/rpc/RpcHandlerManager.ts`
- 文件：`happy-server/sources/app/api/socket/rpcHandler.ts`

Worker 通过 `StatusReporter` + Socket.IO 主动向 Master 报告状态，**不使用 Claude Code Stop Hook**。

```
┌─────────────────────────────────────────────────────────────┐
│                     Master Process                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              SocketServer (Socket.IO)                 │  │
│  │  on('worker:register')      → 注册 Worker             │  │
│  │  on('worker:heartbeat')     → 更新心跳                │  │
│  │  on('worker:task_started')  → 任务开始                │  │
│  │  on('worker:task_completed') → 任务完成 ✅            │  │
│  │  on('worker:task_failed')   → 任务失败                │  │
│  │  on('worker:task_progress') → 进度更新                │  │
│  │  emit('master:task_assign') → 分配任务                │  │
│  │  emit('master:task_cancel') → 取消任务                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↑ WebSocket
                            │
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Worker 1   │    │   Worker 2   │    │   Worker 3   │
│ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │
│ │ Worktree │ │    │ │ Worktree │ │    │ │ Worktree │ │
│ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │
│ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │
│ │ Claude   │ │    │ │ Claude   │ │    │ │ Claude   │ │
│ │ Headless │ │    │ │ Headless │ │    │ │ Headless │ │
│ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │
│ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │
│ │ Status   │ │    │ │ Status   │ │    │ │ Status   │ │
│ │ Reporter │ │    │ │ Reporter │ │    │ │ Reporter │ │
│ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │
└──────────────┘    └──────────────┘    └──────────────┘
```

### StatusReporter 设计（参考 Happy）

```typescript
// src/parallel/worker/StatusReporter.ts
export class StatusReporter {
  private socket: Socket;
  private workerId: string;

  /**
   * 报告任务完成（通过 Socket.IO emit）
   */
  reportTaskCompleted(taskId: string, result: TaskExecutionResult): void {
    this.socket.emit('worker:task_completed', {
      workerId: this.workerId,
      taskId,
      result: {
        success: result.success,
        output: result.output,
        error: result.error
      },
      timestamp: new Date().toISOString()
    });
  }

  /**
   * 报告任务进度
   */
  reportTaskProgress(taskId: string, progress: number, message: string): void {
    this.socket.emit('worker:task_progress', {
      workerId: this.workerId,
      taskId,
      progress,
      message,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * 心跳（30秒间隔）
   */
  startHeartbeat(): void {
    setInterval(() => {
      this.socket.emit('worker:heartbeat', {
        workerId: this.workerId,
        timestamp: new Date().toISOString()
      });
    }, 30000);
  }
}
```

### RPC 支持（可选）

参考 Happy 的 RPC 系统，支持请求-响应模式：
- `socket.emit('rpc-register')` 注册 RPC 方法
- `socket.emit('rpc-call')` 调用远程方法
- `emitWithAck()` 带确认的消息发送

---

## 二、爆改 Task Master（保留 + 简化）

### 设计理念

**基于现有 task-master.dev 代码进行爆改**，而非完全重写：

1. **保留 tasks.json 格式**：继续使用 `.taskmaster/tasks/tasks.json`
2. **保留核心功能**：TaskDAG（依赖图）、TaskScheduler（调度）
3. **简化复杂度**：移除过度设计，保持 YAGNI 原则
4. **重命名适配器**：TaskMasterAdapter → TaskManager

### 保留的 tasks.json 格式

```json
[
  {
    "id": "1",
    "title": "任务1：创建数据库模型",
    "description": "设计并实现用户、订单、产品的数据库模型（无依赖，可立即执行）",
    "status": "pending",
    "priority": 1,
    "dependencies": []
  },
  {
    "id": "2",
    "title": "任务2：实现RESTful API接口",
    "description": "基于数据库模型实现 CRUD API 接口（依赖任务1）",
    "status": "pending",
    "priority": 2,
    "dependencies": ["1"]
  }
]
```

### 爆改策略

| 组件 | 现有代码 | 爆改方案 |
|------|---------|---------|
| **TaskMasterAdapter** | 168 行，加载/保存/验证 | ✅ 保留核心，重命名为 TaskManager |
| **TaskDAG** | 依赖图 + 拓扑排序 | ✅ 完全保留（核心能力） |
| **TaskScheduler** | 3 种调度策略 | ⚡ 简化为 PRIORITY_FIRST + DEPENDENCY_FIRST |
| **Zod Schema** | 运行时验证 | ✅ 保留（重要的安全防护） |
| **时间戳补充** | 自动添加 createdAt/updatedAt | ✅ 保留 |
| **metadata 字段** | estimatedHours, tags | ⚡ 仅保留 estimatedHours |

### 简化后的 TaskManager

```typescript
// src/parallel/task/TaskManager.ts（基于 TaskMasterAdapter 爆改）
export class TaskManager {
  private tasksFile = '.taskmaster/tasks/tasks.json';  // 保持原路径

  // ✅ 保留核心方法
  async loadTasks(): Promise<Task[]>;
  async saveTasks(): Promise<void>;
  tasksFileExists(): Promise<boolean>;

  // ⚡ 简化：移除复杂的序列化逻辑
  // ⚡ 简化：移除多语言支持
  // ⚡ 简化：移除高级调度策略
}
```

### 保留 Tmux 作为核心能力

**为什么保留 Tmux**：
1. **进程隔离**：每个 Worker 在独立的 tmux 会话中运行
2. **输出捕获**：通过 `capture-pane` 获取 Claude 输出
3. **会话持久化**：断开连接后可重新连接
4. **无依赖并行**：只有依赖已满足的任务才能在独立 tmux 中并行执行

```
┌─────────────────────────────────────────────────────────────┐
│                   并行执行控制流程                           │
└─────────────────────────────────────────────────────────────┘

TaskDAG.getReadyTasks()
    │
    ├─ 返回依赖已满足的任务列表
    │   例如：[task-1, task-3, task-5] （无依赖或依赖已完成）
    │
    ↓
TaskScheduler.schedule()
    │
    ├─ 按优先级排序
    ├─ 分配给空闲 Worker
    │
    ↓
WorkerPool.assignTask(worker, task)
    │
    ├─ 每个 Worker 有独立的：
    │   - Git Worktree（代码隔离）
    │   - Tmux 会话（进程隔离）
    │
    ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Tmux: task-1 │  │ Tmux: task-3 │  │ Tmux: task-5 │
│   Worker-1   │  │   Worker-2   │  │   Worker-3   │
│  Worktree-1  │  │  Worktree-2  │  │  Worktree-3  │
└──────────────┘  └──────────────┘  └──────────────┘
      ↓                 ↓                 ↓
   并行执行           并行执行           并行执行
```

### Tmux + Claude Headless 集成

```typescript
// 在 Tmux 会话中启动 Claude Headless
const command = `claude -p "${taskPrompt}" --output-format stream-json --permission-mode acceptEdits`;
await tmuxController.sendCommand(sessionName, command);

// 通过 capture-pane 监控输出
const output = await tmuxController.captureOutput(sessionName);
const completed = isTaskCompleted(output);  // 检测 type === 'result'
```

---

## 三、Claude Code 2025 新能力整合

### 关键能力对照

| Claude Code 能力 | 在 ParallelDev 中的应用 |
|-----------------|----------------------|
| **Headless 模式** | `claude -p` 非交互执行任务 |
| **stream-json** | 实时捕获 Claude 输出 |
| **--resume** | 恢复中断的 Worker 会话 |
| **Subagent** | 自定义 Agent（quality-gate、conflict-resolver） |
| **Skills** | 复杂工作流（parallel-execution、conflict-resolution） |

**注意**：任务完成通知**不使用 Stop Hook**，而是通过 Socket.IO + StatusReporter 实现。

### Headless 模式执行

```typescript
// 启动 Worker（使用 Headless 模式）
const worker = spawn('claude', [
  '-p', taskPrompt,
  '--output-format', 'stream-json',
  '--permission-mode', 'acceptEdits',
  '--allowedTools', 'Read,Edit,Write,Bash,Grep,Glob'
], {
  cwd: worktreePath,
  env: {
    ...process.env,
    PARALLELDEV_WORKER_ID: workerId,
    PARALLELDEV_TASK_ID: taskId,
    PARALLELDEV_MASTER_URL: masterUrl
  }
});

// 实时捕获输出
worker.stdout.on('data', (data) => {
  const events = parseStreamJson(data);
  events.forEach(event => handleWorkerEvent(event));
});
```

### 自定义 Subagent

**质量门禁 Agent**：
```markdown
---
name: quality-gate
description: 代码质量检查专家
tools: Bash, Read, Grep
model: haiku
---

你是代码质量检查专家。执行以下检查：
1. TypeScript 类型检查 (tsc --noEmit)
2. ESLint 检查
3. 单元测试

返回检查报告。
```

**冲突解决 Agent**：
```markdown
---
name: conflict-resolver
description: Git 冲突解决专家
tools: Bash, Read, Edit
model: sonnet
---

你是 Git 冲突解决专家。分析冲突并提供解决方案：
- Level 1: 自动解决简单冲突
- Level 2: 复杂冲突需要分析
- Level 3: 需要人工介入
```

### Skills 集成（自动发现的能力包）

**Skills vs Subagent**：
| 特性 | Skills | Subagent |
|-----|--------|----------|
| 触发方式 | 自动（Claude 判断上下文） | 显式调用 |
| 文件结构 | `SKILL.md` + 支持文件 | 单一 `.md` 文件 |
| 适用场景 | 复杂多步骤工作流 | 特定任务专家 |

**ParallelDev Skills 设计**：

#### 1. parallel-task-execution Skill
```
.claude/skills/parallel-task-execution/
├── SKILL.md                    # 主配置
├── WORKFLOW.md                 # 工作流文档
├── scripts/
│   ├── create-worktree.sh      # 创建 worktree 脚本
│   └── cleanup-worktree.sh     # 清理 worktree 脚本
└── templates/
    └── task-prompt.md          # 任务提示模板
```

**SKILL.md**：
```yaml
---
name: parallel-task-execution
description: Execute development tasks in parallel using Git worktrees. Use when asked to run multiple tasks concurrently, implement features in parallel, or manage parallel development workflows.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Parallel Task Execution

## When to Use
- User asks to run multiple tasks at once
- User mentions "parallel", "concurrent", or "worktree"
- Multiple independent features need implementation

## Workflow
1. Create Git worktree for each task
2. Launch Claude Headless in each worktree
3. Monitor task completion via Stop Hook
4. Merge results back to main branch

See [WORKFLOW.md](WORKFLOW.md) for detailed steps.
```

#### 2. conflict-resolution Skill
```
.claude/skills/conflict-resolution/
├── SKILL.md
├── STRATEGIES.md               # 冲突解决策略
└── scripts/
    └── detect-conflicts.sh     # 冲突检测脚本
```

**SKILL.md**：
```yaml
---
name: conflict-resolution
description: Resolve Git merge conflicts intelligently. Use when git conflicts are detected, merge fails, or rebase has conflicts.
allowed-tools: Bash, Read, Edit, Grep
---

# Conflict Resolution

## Strategies
- **Level 1**: Auto-resolve (formatting, lockfiles)
- **Level 2**: AI-assisted (semantic conflicts)
- **Level 3**: Human required (complex logic)

See [STRATEGIES.md](STRATEGIES.md) for details.
```

#### 3. quality-assurance Skill
```
.claude/skills/quality-assurance/
├── SKILL.md
├── CHECKS.md                   # 检查项清单
└── scripts/
    ├── run-lint.sh
    ├── run-typecheck.sh
    └── run-tests.sh
```

**SKILL.md**：
```yaml
---
name: quality-assurance
description: Run comprehensive code quality checks. Use before merging, after task completion, or when quality verification is needed.
allowed-tools: Bash, Read, Grep
---

# Quality Assurance

## Checks
1. TypeScript type checking
2. ESLint code style
3. Unit tests
4. Integration tests

See [CHECKS.md](CHECKS.md) for configuration.
```

### Skills vs Subagent 选择策略

| 场景 | 推荐 | 原因 |
|-----|------|------|
| 并行任务执行 | **Skill** | 复杂多步骤工作流，需要脚本支持 |
| 冲突解决 | **Skill** | 有多种策略，需要文档 |
| 质量检查 | **Skill** | 需要脚本和配置文件 |
| 简单代码审查 | **Subagent** | 单一专家角色 |
| 快速问答 | **Subagent** | 简单任务 |

---

## 四、清空文件清单

### 需要删除的 23 个文件

```
src/parallel/
├── config.ts                      ❌ 删除
├── types.ts                       ❌ 删除
├── index.ts                       ❌ 删除
├── git/
│   ├── WorktreeManager.ts         ❌ 删除
│   ├── ConflictDetector.ts        ❌ 删除
│   └── ConflictResolver.ts        ❌ 删除
├── master/
│   ├── MasterOrchestrator.ts      ❌ 删除
│   ├── StateManager.ts            ❌ 删除
│   └── WorkerPool.ts              ❌ 删除
├── worker/
│   ├── WorkerAgent.ts             ❌ 删除
│   ├── TaskExecutor.ts            ❌ 删除
│   └── StatusReporter.ts          ❌ 删除
├── task/
│   ├── TaskDAG.ts                 ❌ 删除
│   ├── TaskScheduler.ts           ❌ 删除
│   ├── TaskMasterAdapter.ts       ❌ 删除
│   ├── TaskDAG.test.ts            ❌ 删除
│   └── TaskScheduler.test.ts      ❌ 删除
├── tmux/
│   ├── TmuxController.ts          ❌ 删除
│   └── SessionMonitor.ts          ❌ 删除
├── quality/
│   └── CodeValidator.ts           ❌ 删除
├── notification/
│   ├── NotificationManager.ts     ❌ 删除
│   └── ReportGenerator.ts         ❌ 删除
└── web/
    └── MonitorServer.ts           ❌ 删除
```

**同时删除**：`src/cli-parallel.ts`

---

## 五、6 层架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                  Layer 1: Task Management                   │
│  TaskDAG.ts | TaskScheduler.ts | TaskManager.ts             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 爆改 Task Master（保留 + 简化）                       │    │
│  │  • .taskmaster/tasks/tasks.json 任务定义             │    │
│  │  • DAG 依赖图 + 拓扑排序（保留）                      │    │
│  │  • 优先级调度（简化）                                 │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Layer 2: Orchestration                     │
│  MasterOrchestrator.ts | WorkerPool.ts | StateManager.ts    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Layer 3: Execution                       │
│  WorktreeManager.ts | TmuxController.ts | TaskExecutor.ts   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Tmux 核心能力（保留）                                 │    │
│  │  • 进程隔离：每个 Worker 独立 tmux 会话              │    │
│  │  • 输出捕获：capture-pane 获取 Claude 输出           │    │
│  │  • 会话持久化：断开后可重连                          │    │
│  │  • 无依赖并行：只有 ready 任务才能并行               │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Claude Headless 在 Tmux 中执行                       │    │
│  │  • claude -p --output-format stream-json             │    │
│  │  • --permission-mode acceptEdits                     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│       Layer 4: Communication (Socket.IO + RPC)              │
│  SocketServer.ts | StatusReporter.ts | SessionMonitor.ts    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Happy 风格通信                                       │    │
│  │  • Socket.IO 双向通信                                │    │
│  │  • StatusReporter 主动上报                           │    │
│  │  • SessionMonitor 监控 Tmux 输出（15秒轮询）         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│       Layer 5: Quality Assurance (Subagent 驱动)            │
│  SubagentRunner.ts | ConflictResolver.ts | CodeValidator.ts │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Custom Subagents (.claude/agents/)                   │    │
│  │  • quality-gate.md → 代码质量检查                    │    │
│  │  • conflict-resolver.md → 冲突解决                   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Layer 6: Notification                     │
│  NotificationManager.ts | ReportGenerator.ts                │
└─────────────────────────────────────────────────────────────┘
```

### 技术方案与架构层对应

| 架构层 | 技术方案 | 作用 |
|-------|---------|------|
| Layer 1 | **爆改 TaskManager** | 保留 tasks.json 格式，简化调度策略 |
| Layer 1 | **TaskDAG** | 依赖图 + 拓扑排序（完全保留） |
| Layer 3 | **TmuxController** | 会话创建/销毁/命令执行（保留） |
| Layer 3 | **Tmux + Headless** | 在 Tmux 中执行 `claude -p` |
| Layer 3 | **WorktreeManager** | Git Worktree 隔离 |
| Layer 4 | **Socket.IO + StatusReporter** | 任务完成通知（Happy 风格） |
| Layer 4 | **SessionMonitor** | 监控 Tmux 输出（保留） |
| Layer 5 | **Custom Subagent** | quality-gate, conflict-resolver |
| Layer 5 | **Skills** | 复杂工作流自动触发 |

---

## 六、新文件结构

```
src/parallel/
├── index.ts                       # 模块导出
├── types.ts                       # 核心类型定义
├── config.ts                      # 配置管理
│
├── task/                          # Layer 1: 任务管理（爆改 Task Master）
│   ├── TaskDAG.ts                 # 任务依赖图（保留）
│   ├── TaskScheduler.ts           # 任务调度器（简化）
│   └── TaskManager.ts             # 任务管理器（爆改自 TaskMasterAdapter）
│
├── master/                        # Layer 2: 编排控制
│   ├── MasterOrchestrator.ts      # 主编排器
│   ├── WorkerPool.ts              # Worker 池管理
│   └── StateManager.ts            # 状态持久化
│
├── git/                           # Layer 3: Git 集成
│   ├── WorktreeManager.ts         # Git Worktree 管理
│   └── ConflictDetector.ts        # 冲突检测
│
├── tmux/                          # Layer 3: Tmux 核心能力（保留）
│   ├── TmuxController.ts          # 会话创建/销毁/命令执行
│   └── SessionMonitor.ts          # 输出监控（15秒轮询）
│
├── worker/                        # Layer 3+4: Worker 执行
│   ├── TaskExecutor.ts            # 在 Tmux 中执行 Claude Headless
│   ├── WorkerAgent.ts             # Worker 主控制器
│   └── StatusReporter.ts          # 状态上报（Socket.IO）
│
├── communication/                 # Layer 4: 通信层
│   ├── SocketServer.ts            # Socket.IO 服务器
│   └── MessageProtocol.ts         # 消息协议定义
│
├── quality/                       # Layer 5: 质量保证
│   ├── SubagentRunner.ts          # Subagent 执行器
│   ├── ConflictResolver.ts        # 冲突解决（调用 Subagent）
│   └── CodeValidator.ts           # 代码验证（调用 Subagent）
│
└── notification/                  # Layer 6: 通知报告
    ├── NotificationManager.ts     # 通知管理
    └── ReportGenerator.ts         # 报告生成
```

**CLI 入口**：`src/cli-parallel.ts`

**任务配置目录**（保持原路径）：
```
.taskmaster/
├── tasks/
│   └── tasks.json                 # 任务定义文件（保持原格式）
```

**运行状态目录**：
```
.paralleldev/
├── state.json                     # 运行状态持久化
└── config.json                    # 项目配置
```

**Claude Code Plugin 架构**（核心扩展方式）：

```
paralleldev-plugin/                    # Plugin 根目录
├── .claude-plugin/
│   └── plugin.json                    # Plugin 元数据（必须）
│
├── commands/                          # 斜杠命令（/pd:xxx）
│   ├── start.md                       # /pd:start - 启动并行执行
│   ├── status.md                      # /pd:status - 查看状态
│   ├── assign.md                      # /pd:assign - 分配任务
│   ├── stop.md                        # /pd:stop - 停止执行
│   └── report.md                      # /pd:report - 生成报告
│
├── agents/                            # 子智能体（显式/自动调用）
│   ├── task-orchestrator.md           # 任务编排专家
│   ├── quality-gate.md                # 质量门禁专家
│   ├── conflict-resolver.md           # 冲突解决专家
│   └── worker-monitor.md              # Worker 监控专家
│
├── skills/                            # 能力扩展（model-invoked 自动调用）
│   ├── parallel-executor/             # 并行执行能力
│   │   ├── SKILL.md
│   │   ├── WORKFLOW.md
│   │   └── scripts/
│   │       ├── create-worktree.sh
│   │       └── cleanup-worktree.sh
│   │
│   ├── conflict-resolution/           # 冲突解决能力
│   │   ├── SKILL.md
│   │   ├── STRATEGIES.md
│   │   └── scripts/
│   │       └── detect-conflicts.sh
│   │
│   └── quality-assurance/             # 质量保证能力
│       ├── SKILL.md
│       ├── CHECKS.md
│       └── scripts/
│           ├── run-lint.sh
│           ├── run-typecheck.sh
│           └── run-tests.sh
│
├── hooks/
│   └── hooks.json                     # 事件处理（任务完成、冲突检测）
│
├── .mcp.json                          # MCP 服务器配置（连接 Master/Worker）
│
├── scripts/                           # 支持脚本
│   ├── master-start.sh                # 启动 Master
│   ├── worker-start.sh                # 启动 Worker
│   └── cleanup.sh                     # 清理资源
│
└── README.md                          # Plugin 文档
```

### Plugin 核心配置文件

#### 1. plugin.json（Plugin 元数据）
```json
{
  "name": "paralleldev",
  "version": "1.0.0",
  "description": "Claude Code 自动化并行开发系统 - 通过 git worktree + tmux + Socket.IO 实现真正的并行开发",
  "author": {
    "name": "ParallelDev Team"
  },
  "homepage": "https://github.com/your-org/paralleldev-plugin",
  "license": "MIT",
  "keywords": ["parallel", "development", "worktree", "automation", "claude-code"],
  "commands": "./commands/",
  "agents": "./agents/",
  "hooks": "./hooks/hooks.json",
  "mcpServers": "./.mcp.json"
}
```

#### 2. 斜杠命令定义

**commands/start.md**：
```markdown
---
description: 启动 ParallelDev 并行执行系统，创建 Workers 并开始任务调度
---

# /pd:start 命令

启动 ParallelDev 系统：
1. 读取 .taskmaster/tasks/tasks.json 任务列表
2. 创建指定数量的 Workers（默认 3 个）
3. 为每个 Worker 创建独立的 git worktree
4. 启动 Master 编排器开始任务调度
5. 通过 Socket.IO 建立 Master-Worker 通信

参数：
- --workers <n>: Worker 数量（默认 3）
- --strategy <priority|dependency>: 调度策略（默认 priority）
```

**commands/status.md**：
```markdown
---
description: 查看当前 ParallelDev 运行状态，包括任务进度和 Worker 状态
---

# /pd:status 命令

显示当前系统状态：
1. 总任务数、完成数、进行中、待处理
2. 每个 Worker 的状态（idle/busy/error）
3. 当前正在执行的任务详情
4. 预计完成时间
```

#### 3. 子智能体定义

**agents/task-orchestrator.md**：
```markdown
---
description: 任务编排专家，负责分析任务依赖、制定执行计划、协调并行执行。当需要规划并行任务执行策略时自动激活。
capabilities: ["task-planning", "dependency-analysis", "parallel-coordination"]
model: sonnet
---

# Task Orchestrator Agent

你是 ParallelDev 的任务编排专家。你的职责是：

1. **依赖分析**：分析任务 DAG，识别可并行执行的任务
2. **执行规划**：制定最优的并行执行计划
3. **资源分配**：将任务分配给可用的 Workers
4. **进度监控**：跟踪任务完成情况，动态调整计划

工作流程：
1. 读取 .taskmaster/tasks/tasks.json
2. 构建任务依赖图（DAG）
3. 执行拓扑排序，识别可立即执行的任务
4. 按优先级排序，分配给空闲 Workers
5. 监控完成情况，持续调度新任务
```

**agents/quality-gate.md**：
```markdown
---
description: 代码质量门禁专家，负责在任务完成后执行质量检查。当代码变更需要验证时自动激活。
capabilities: ["code-review", "type-checking", "lint-checking", "test-running"]
model: haiku
---

# Quality Gate Agent

你是代码质量门禁专家。在每个任务完成后执行：

1. **TypeScript 检查**：`tsc --noEmit`
2. **ESLint 检查**：`eslint --ext .ts,.tsx`
3. **单元测试**：`npm test -- --coverage`
4. **集成测试**：`npm run test:integration`

输出格式：
- ✅ 通过：继续下一步
- ⚠️ 警告：报告问题但不阻塞
- ❌ 失败：阻塞合并，需要修复
```

**agents/conflict-resolver.md**：
```markdown
---
description: Git 冲突解决专家，负责检测和解决并行开发产生的代码冲突。当检测到 merge 冲突时自动激活。
capabilities: ["conflict-detection", "conflict-resolution", "merge-strategy"]
model: sonnet
---

# Conflict Resolver Agent

你是 Git 冲突解决专家。采用分层策略：

## Level 1: 自动解决（无需人工）
- 格式化差异（空格、换行）
- package-lock.json / yarn.lock
- 自动生成的文件

## Level 2: AI 辅助解决
- 语义冲突（同一函数的不同修改）
- 导入语句冲突
- 配置文件冲突

## Level 3: 人工介入
- 业务逻辑冲突
- 架构变更冲突
- 无法自动判断的情况

处理流程：
1. 执行 `git diff --name-only --diff-filter=U` 检测冲突文件
2. 分析冲突类型和复杂度
3. 根据级别选择解决策略
4. 执行解决并验证
```

#### 4. Skills 定义

**skills/parallel-executor/SKILL.md**：
```yaml
---
name: parallel-executor
description: 并行任务执行能力。当用户请求并行开发、创建 worktree、或执行多个独立任务时自动激活。
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Parallel Executor Skill

## 触发条件
- 用户提到 "parallel", "并行", "worktree"
- 需要同时处理多个独立任务
- 请求创建隔离的开发环境

## 工作流程
1. 创建 Git Worktree：`git worktree add .worktrees/<task-id> -b task/<task-id>`
2. 启动 Tmux 会话：`tmux new-session -d -s parallel-dev-<worker-id>`
3. 在 Worktree 中执行 Claude Headless
4. 通过 Socket.IO 上报任务状态
5. 完成后清理 Worktree

参考 [WORKFLOW.md](WORKFLOW.md) 了解详细步骤。
```

#### 5. Hooks 配置

**hooks/hooks.json**：
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/notify-change.sh \"$TOOL_NAME\" \"$FILE_PATH\""
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/task-completed.sh \"$TASK_ID\" \"$RESULT\""
          }
        ]
      }
    ]
  }
}
```

#### 6. MCP 服务器配置

**.mcp.json**：
```json
{
  "mcpServers": {
    "paralleldev-master": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/../src/parallel/mcp/master-server.js"],
      "env": {
        "SOCKET_PORT": "3001",
        "STATE_FILE": "${PROJECT_ROOT}/.paralleldev/state.json"
      }
    }
  }
}
```

### Plugin vs 独立 .claude/ 目录

| 方式 | 适用场景 | 优势 |
|-----|---------|------|
| **Plugin** | 团队共享、跨项目复用 | Marketplace 分发、版本管理、统一配置 |
| **独立 .claude/** | 项目特定配置 | 简单直接、无需安装 |

**推荐**：使用 Plugin 方式，便于团队协作和版本管理。

### 项目内 .claude/ 目录（补充配置）

```
.claude/
├── settings.json                  # 项目设置（启用 plugin）
└── agents/                        # 项目特定 agents（可选）
    └── project-specific.md
```

**settings.json**：
```json
{
  "plugins": ["paralleldev@your-marketplace"],
  "extraKnownMarketplaces": ["https://github.com/your-org/claude-plugins"]
}
```

---

## 四、核心类型定义

```typescript
// src/parallel/types.ts

/** 任务状态 */
export type TaskStatus =
  | 'pending'      // 等待执行
  | 'ready'        // 依赖已满足，可执行
  | 'running'      // 正在执行
  | 'completed'    // 已完成
  | 'failed'       // 已失败
  | 'cancelled';   // 已取消

/** 任务定义 */
export interface Task {
  id: string;
  title: string;
  description: string;
  dependencies: string[];
  priority: number;
  status: TaskStatus;
  assignedWorker?: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  error?: string;
}

/** Worker 状态 */
export type WorkerStatus =
  | 'idle'         // 空闲
  | 'busy'         // 忙碌
  | 'error'        // 错误
  | 'offline';     // 离线

/** Worker 定义 */
export interface Worker {
  id: string;
  status: WorkerStatus;
  worktreePath: string;
  tmuxSession: string;
  currentTaskId?: string;
  lastHeartbeat: string;
}

/** Worker → Master 事件 */
export interface WorkerEvent {
  type: 'task_started' | 'task_completed' | 'task_failed' | 'heartbeat' | 'progress';
  workerId: string;
  taskId?: string;
  timestamp: string;
  payload?: {
    output?: string;
    error?: string;
    progress?: number;
  };
}

/** Master → Worker 命令 */
export interface MasterCommand {
  type: 'task_assign' | 'task_cancel' | 'worker_terminate';
  taskId?: string;
  task?: Task;
}

/** 配置 */
export interface ParallelDevConfig {
  maxWorkers: number;
  worktreeDir: string;
  mainBranch: string;
  socketPort: number;
  heartbeatInterval: number;
  taskTimeout: number;
}
```

---

## 五、通信架构（Socket.IO + RPC）

### 参考 Happy 项目

```
┌─────────────────────────────────────────────────────────────┐
│                     Master Process                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              SocketServer (Socket.IO)                 │  │
│  │  on('worker:register')    → 注册 Worker               │  │
│  │  on('worker:heartbeat')   → 更新心跳                  │  │
│  │  on('worker:task_started') → 任务开始                 │  │
│  │  on('worker:task_completed') → 任务完成               │  │
│  │  on('worker:task_failed')   → 任务失败                │  │
│  │  emit('master:task_assign') → 分配任务                │  │
│  │  emit('master:task_cancel') → 取消任务                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↑ WebSocket
                            │
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Worker 1   │    │   Worker 2   │    │   Worker 3   │
│ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │
│ │ Worktree │ │    │ │ Worktree │ │    │ │ Worktree │ │
│ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │
│ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │
│ │   Tmux   │ │    │ │   Tmux   │ │    │ │   Tmux   │ │
│ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │
│ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │
│ │  Claude  │ │    │ │  Claude  │ │    │ │  Claude  │ │
│ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │
│ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │
│ │RPC Client│ │    │ │RPC Client│ │    │ │RPC Client│ │
│ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 事件驱动流程

```
1. Master 启动 SocketServer
2. Worker 启动 → 连接 Socket → 发送 register
3. Master 分配任务 → emit('master:task_assign')
4. Worker 开始执行 → emit('worker:task_started')
5. Worker 完成/失败 → emit('worker:task_completed/failed')
6. Master 更新状态 → 调度下一个任务
7. Worker 定期发送 heartbeat（30秒）
```

---

## 八、详细实施计划（TODO 列表）

---

### Phase 0: Pull 代码（前置步骤）

**目标**：从外部仓库 Pull 代码到项目中，为后续爆改做准备

#### TODO 0.1: Clone task-master 仓库
- [ ] 执行 `git clone https://github.com/eyaltoledano/claude-task-master.git /tmp/claude-task-master`
- [ ] 验证 clone 成功

#### TODO 0.2: 分析 task-master 源码结构
- [ ] 执行 `find /tmp/claude-task-master -name "*.ts" -path "*/src/*" | head -50`
- [ ] 找到 TaskDAG 相关文件（依赖图实现）
- [ ] 找到 TaskScheduler 相关文件（调度器实现）
- [ ] 找到任务类型定义文件
- [ ] 记录需要复制的文件列表

#### TODO 0.3: 复制 task-master 核心文件
- [ ] 创建 `src/parallel/task/` 目录（如不存在）
- [ ] 复制依赖图实现到 `src/parallel/task/TaskDAG.ts`（或与现有版本对比后保留更优的）
- [ ] 复制调度器实现到 `src/parallel/task/TaskScheduler.ts`
- [ ] 复制类型定义

#### TODO 0.4: 复制 Happy Socket.IO 客户端代码
- [ ] 读取 `happy/sources/sync/apiSocket.ts`（262行）
- [ ] 创建 `src/parallel/communication/` 目录
- [ ] 复制到 `src/parallel/communication/SocketClient.ts`
- [ ] 记录需要移除的代码段（加密、认证）

#### TODO 0.5: 复制 RPC 管理器代码
- [ ] 读取 `src/api/rpc/RpcHandlerManager.ts`（135行）
- [ ] 复制到 `src/parallel/communication/RpcManager.ts`
- [ ] 记录需要移除的代码段（加密）

#### TODO 0.6: 复制 RPC 类型定义
- [ ] 读取 `src/api/rpc/types.ts`
- [ ] 复制到 `src/parallel/communication/rpc-types.ts`

**Phase 0 验收标准**：
- [ ] `/tmp/claude-task-master` 目录存在
- [ ] `src/parallel/communication/SocketClient.ts` 存在
- [ ] `src/parallel/communication/RpcManager.ts` 存在
- [ ] `src/parallel/communication/rpc-types.ts` 存在

---

### Phase 1: 基础设施 + Claude 配置

**目标**：建立项目骨架、核心类型、Claude 配置

#### TODO 1.1: 清理无用文件
- [ ] 列出 `src/parallel/` 下所有文件
- [ ] 识别需要删除的文件（web/MonitorServer.ts 等）
- [ ] 识别需要保留/爆改的文件
- [ ] 执行删除操作
- [ ] 验证目录结构

#### TODO 1.2: 爆改 types.ts
- [ ] 读取现有 `src/parallel/types.ts`（292行）
- [ ] 移除 TaskStatus 枚举，改为字符串联合类型
- [ ] 简化 Task 接口（保留 id, title, description, dependencies, priority, status）
- [ ] 简化 Worker 接口
- [ ] 移除复杂的消息类型（BaseMessage 等），改用简单的事件类型
- [ ] 保留 Zod Schema（用于运行时验证）
- [ ] 添加 Socket.IO 事件类型定义

#### TODO 1.3: 爆改 config.ts
- [ ] 读取现有 `src/parallel/config.ts`
- [ ] 简化配置结构（maxWorkers, worktreeDir, mainBranch, socketPort）
- [ ] 添加默认配置
- [ ] 添加配置加载函数

#### TODO 1.4: 创建 index.ts
- [ ] 创建模块导出文件
- [ ] 导出所有公共 API

#### TODO 1.5: 创建运行状态模板
- [ ] 创建 `.paralleldev/` 目录
- [ ] 创建 `state.json` 模板（workers: [], tasks: [], currentPhase）
- [ ] 创建 `config.json` 模板

#### TODO 1.6: 创建 Plugin 基础结构
- [ ] 创建 `paralleldev-plugin/` 目录
- [ ] 创建 `paralleldev-plugin/.claude-plugin/` 目录
- [ ] 创建 `plugin.json` 元数据文件：
  ```json
  {
    "name": "paralleldev",
    "version": "1.0.0",
    "description": "Claude Code 自动化并行开发系统",
    "author": { "name": "ParallelDev Team" },
    "commands": "./commands/",
    "agents": "./agents/",
    "hooks": "./hooks/hooks.json",
    "mcpServers": "./.mcp.json"
  }
  ```

#### TODO 1.7: 创建 Plugin 斜杠命令
- [ ] 创建 `paralleldev-plugin/commands/` 目录
- [ ] 创建 `start.md`：
  - [ ] description: 启动并行执行系统
  - [ ] 指令：读取任务、创建 Workers、启动调度
  - [ ] 参数：--workers, --strategy
- [ ] 创建 `status.md`：
  - [ ] description: 查看运行状态
  - [ ] 指令：显示任务进度、Worker 状态
- [ ] 创建 `assign.md`：
  - [ ] description: 手动分配任务
  - [ ] 指令：将指定任务分配给指定 Worker
- [ ] 创建 `stop.md`：
  - [ ] description: 停止执行
  - [ ] 指令：优雅停止所有 Workers
- [ ] 创建 `report.md`：
  - [ ] description: 生成报告
  - [ ] 指令：生成执行报告

#### TODO 1.8: 创建 Plugin Agents
- [ ] 创建 `paralleldev-plugin/agents/` 目录
- [ ] 创建 `task-orchestrator.md`：
  - [ ] description: 任务编排专家
  - [ ] capabilities: task-planning, dependency-analysis
  - [ ] model: sonnet
  - [ ] 指令：依赖分析、执行规划、资源分配
- [ ] 创建 `quality-gate.md`：
  - [ ] description: 代码质量门禁专家
  - [ ] capabilities: code-review, type-checking
  - [ ] model: haiku
  - [ ] 指令：TypeScript 检查、ESLint、单元测试
- [ ] 创建 `conflict-resolver.md`：
  - [ ] description: Git 冲突解决专家
  - [ ] capabilities: conflict-detection, conflict-resolution
  - [ ] model: sonnet
  - [ ] 指令：分层解决策略（Level 1/2/3）
- [ ] 创建 `worker-monitor.md`：
  - [ ] description: Worker 监控专家
  - [ ] capabilities: monitoring, health-check
  - [ ] model: haiku
  - [ ] 指令：健康检查、状态监控、异常检测

#### TODO 1.9: 创建 Plugin Skills
- [ ] 创建 `paralleldev-plugin/skills/` 目录
- [ ] 创建 `parallel-executor/` Skill：
  - [ ] `SKILL.md`：name, description, allowed-tools, 触发条件
  - [ ] `WORKFLOW.md`：详细工作流程文档
  - [ ] `scripts/create-worktree.sh`：创建 worktree 脚本
  - [ ] `scripts/cleanup-worktree.sh`：清理 worktree 脚本
- [ ] 创建 `conflict-resolution/` Skill：
  - [ ] `SKILL.md`：冲突解决能力定义
  - [ ] `STRATEGIES.md`：分层解决策略文档
  - [ ] `scripts/detect-conflicts.sh`：冲突检测脚本
- [ ] 创建 `quality-assurance/` Skill：
  - [ ] `SKILL.md`：质量保证能力定义
  - [ ] `CHECKS.md`：检查项配置
  - [ ] `scripts/run-lint.sh`
  - [ ] `scripts/run-typecheck.sh`
  - [ ] `scripts/run-tests.sh`

#### TODO 1.9.1: 创建 Frontend Development Skill（从 CLAUDE_fronted.md 提取）
- [ ] 创建 `paralleldev-plugin/skills/frontend-development/` 目录
- [ ] 创建 `SKILL.md`：
  ```yaml
  ---
  name: frontend-development
  description: 前端开发规范能力。当用户请求开发 React/Vue/Nuxt3/TypeScript 前端代码时自动激活。
  allowed-tools: Read, Write, Edit, Bash, Grep, Glob
  ---
  ```
- [ ] 创建 `RULES.md`：从 `claude_template/CLAUDE_fronted.md` 提取核心规则
  - [ ] YAGNI + KISS + SOLID 原则
  - [ ] 函数 50 行限制
  - [ ] 禁止 `any` 类型
  - [ ] Tailwind CSS v4 标准
  - [ ] 性能指标（FCP, TTI, LCP, CLS, FID）
  - [ ] 组件标准和 Hooks 模式
  - [ ] XSS/CSRF 安全规则
- [ ] 创建 `TEMPLATES.md`：组件模板和代码示例

#### TODO 1.9.2: 创建 Go Development Skill（从 CLAUDE_GO.md 提取）
- [ ] 创建 `paralleldev-plugin/skills/go-development/` 目录
- [ ] 创建 `SKILL.md`：
  ```yaml
  ---
  name: go-development
  description: Go 开发规范能力。当用户请求开发 Go 1.23+ 代码时自动激活。
  allowed-tools: Read, Write, Edit, Bash, Grep, Glob
  ---
  ```
- [ ] 创建 `RULES.md`：从 `claude_template/CLAUDE_GO.md` 提取核心规则
  - [ ] Go 1.23.0+ 特性
  - [ ] Gin + GORM 框架规范
  - [ ] 函数 50 行限制
  - [ ] 禁止 `map[string]interface{}`
  - [ ] 禁止 `interface{}` 参数
  - [ ] Interface+Implementation 模式
  - [ ] 结构体标签标准（json, gorm, binding, validate）
- [ ] 创建 `TEMPLATES.md`：Go 代码注释模板

#### TODO 1.9.3: 创建 Java Development Skill（从 CLAUDE_java.md 提取）
- [ ] 创建 `paralleldev-plugin/skills/java-development/` 目录
- [ ] 创建 `SKILL.md`：
  ```yaml
  ---
  name: java-development
  description: Java 开发规范能力。当用户请求开发 Java JDK 17+ 代码时自动激活。
  allowed-tools: Read, Write, Edit, Bash, Grep, Glob
  ---
  ```
- [ ] 创建 `RULES.md`：从 `claude_template/CLAUDE_java.md` 提取核心规则
  - [ ] JDK 17 特性
  - [ ] 函数 50 行限制
  - [ ] 禁止 `Map<String, Object>`
  - [ ] 扁平化 DTO 设计
  - [ ] Interface+Implementation 模式
  - [ ] @Override 强制要求
- [ ] 创建 `TEMPLATES.md`：Javadoc 模板（类、接口、枚举、注解、异常）

#### TODO 1.9.4: 创建 TypeScript Development Skill（从 CLAUDE.md 提取）
- [ ] 创建 `paralleldev-plugin/skills/typescript-development/` 目录
- [ ] 创建 `SKILL.md`：
  ```yaml
  ---
  name: typescript-development
  description: TypeScript 开发规范能力。当用户请求开发 TypeScript/Node.js 后端代码时自动激活。
  allowed-tools: Read, Write, Edit, Bash, Grep, Glob
  ---
  ```
- [ ] 创建 `RULES.md`：从 `claude_template/CLAUDE.md` 提取核心规则
  - [ ] 6 层架构设计
  - [ ] 函数 50 行限制
  - [ ] 禁止 `any` 类型
  - [ ] JSDoc + 步骤注释
  - [ ] 事件驱动架构
  - [ ] 错误处理规范
- [ ] 创建 `TEMPLATES.md`：TypeScript 文件模板

#### TODO 1.10: 创建 Plugin Hooks 和 MCP 配置
- [ ] 创建 `paralleldev-plugin/hooks/` 目录
- [ ] 创建 `hooks.json`：
  - [ ] PostToolUse hook：监控 Write/Edit 操作
  - [ ] Stop hook：任务完成通知
- [ ] 创建 `paralleldev-plugin/.mcp.json`：
  - [ ] 配置 paralleldev-master MCP 服务器
  - [ ] 设置 SOCKET_PORT、STATE_FILE 环境变量

#### TODO 1.11: 创建 Plugin 支持脚本
- [ ] 创建 `paralleldev-plugin/scripts/` 目录
- [ ] 创建 `master-start.sh`：启动 Master 进程
- [ ] 创建 `worker-start.sh`：启动 Worker 进程
- [ ] 创建 `cleanup.sh`：清理所有资源
- [ ] 创建 `notify-change.sh`：文件变更通知
- [ ] 创建 `task-completed.sh`：任务完成通知

#### TODO 1.12: 配置项目 .claude/ 目录
- [ ] 创建 `.claude/settings.json`：
  ```json
  {
    "plugins": ["paralleldev@local"],
    "extraKnownMarketplaces": []
  }
  ```
- [ ] 创建本地 marketplace 用于测试：
  - [ ] 创建 `test-marketplace/` 目录
  - [ ] 创建 `.claude-plugin/marketplace.json`

#### TODO 1.13: 创建 Plugin README
- [ ] 创建 `paralleldev-plugin/README.md`
- [ ] 包含：功能说明、安装方法、使用示例、配置说明

**Phase 1 验收标准**：
- [ ] `src/parallel/types.ts` 简化完成
- [ ] `src/parallel/config.ts` 简化完成
- [ ] `.paralleldev/` 目录和模板文件存在
- [ ] `paralleldev-plugin/` 目录结构完整：
  - [ ] `.claude-plugin/plugin.json` 存在
  - [ ] `commands/` 包含 5 个命令文件
  - [ ] `agents/` 包含 4 个 Agent 文件
  - [ ] `skills/` 包含 7 个 Skill 目录（3 原有 + 4 语言相关）：
    - [ ] `parallel-executor/`
    - [ ] `conflict-resolution/`
    - [ ] `quality-assurance/`
    - [ ] `frontend-development/`（新增）
    - [ ] `go-development/`（新增）
    - [ ] `java-development/`（新增）
    - [ ] `typescript-development/`（新增）
  - [ ] `hooks/hooks.json` 存在
  - [ ] `.mcp.json` 存在
  - [ ] `scripts/` 包含 5 个脚本
- [ ] Plugin 可以在 Claude Code 中加载测试

**🔍 Phase 1 验证（使用 Claude Task Agent）**：
```bash
# 使用 task-checker agent 验证 Phase 1 完成情况
claude task verify-phase --phase=1 --checklist="types.ts,config.ts,plugin-structure,skills"
```
验证项：
- [ ] 运行 `tsc --noEmit` 验证类型定义
- [ ] 验证 Plugin 目录结构完整性
- [ ] 验证所有 Skills 的 SKILL.md 和 RULES.md 存在
- [ ] 加载 Plugin 测试

---

### Phase 2: Layer 1 任务管理（爆改代码）

**目标**：实现任务依赖图和调度器

#### TODO 2.1: 爆改/保留 TaskDAG.ts
- [ ] 读取现有 `src/parallel/task/TaskDAG.ts`
- [ ] 对比 task-master 版本
- [ ] 选择更优的实现（或合并优点）
- [ ] 确保包含：
  - [ ] addTask() - 添加任务
  - [ ] getReadyTasks() - 获取可执行任务（无依赖或依赖已完成）
  - [ ] markCompleted() - 标记完成
  - [ ] markFailed() - 标记失败
  - [ ] hasCycle() - 检测循环依赖
  - [ ] topologicalSort() - 拓扑排序
- [ ] 编写单元测试

#### TODO 2.2: 爆改 TaskScheduler.ts
- [ ] 读取现有 `src/parallel/task/TaskScheduler.ts`
- [ ] 移除 LOAD_BALANCED 策略
- [ ] 保留 PRIORITY_FIRST 策略
- [ ] 保留 DEPENDENCY_FIRST 策略
- [ ] 简化接口：
  - [ ] schedule(tasks: Task[], availableWorkers: number) → Task[]
  - [ ] setStrategy(strategy: 'priority' | 'dependency') → void
- [ ] 编写单元测试

#### TODO 2.3: 爆改 TaskManager.ts（原 TaskMasterAdapter）
- [ ] 读取现有 `src/parallel/task/TaskMasterAdapter.ts`（168行）
- [ ] 重命名为 TaskManager
- [ ] 保留核心方法：
  - [ ] loadTasks() - 从 .taskmaster/tasks/tasks.json 加载
  - [ ] saveTasks() - 保存到 tasks.json
  - [ ] tasksFileExists() - 检查文件是否存在
  - [ ] validateTask() - 使用 Zod 验证任务
- [ ] 移除复杂的序列化逻辑
- [ ] 简化时间戳处理
- [ ] 编写单元测试

**Phase 2 验收标准**：
- [ ] `TaskDAG.getReadyTasks()` 能正确返回可执行任务
- [ ] `TaskScheduler.schedule()` 能按策略排序任务
- [ ] `TaskManager.loadTasks()` 能加载 tasks.json
- [ ] 所有单元测试通过

**🔍 Phase 2 验证（使用 Claude Task Agent）**：
```bash
claude task verify-phase --phase=2 --run-tests --check-coverage
```
验证项：
- [ ] 运行 `npm test -- --grep="TaskDAG|TaskScheduler|TaskManager"`
- [ ] 验证测试覆盖率 ≥ 80%
- [ ] 验证 tasks.json 加载功能

---

### Phase 3: Layer 3 执行层（Tmux + Worktree）

**目标**：实现 Git Worktree 管理和 Tmux 会话控制

#### TODO 3.1: 爆改 WorktreeManager.ts
- [ ] 读取现有 `src/parallel/git/WorktreeManager.ts`
- [ ] 简化为核心方法：
  - [ ] create(taskId: string, branch: string) → WorktreeInfo
  - [ ] remove(taskId: string) → void
  - [ ] list() → WorktreeInfo[]
  - [ ] exists(taskId: string) → boolean
- [ ] 实现 Git 命令封装：
  - [ ] `git worktree add .worktrees/<taskId> -b task/<taskId>`
  - [ ] `git worktree remove .worktrees/<taskId>`
  - [ ] `git worktree list`
- [ ] 添加错误处理
- [ ] 编写单元测试

#### TODO 3.2: 爆改 ConflictDetector.ts
- [ ] 读取现有 `src/parallel/git/ConflictDetector.ts`
- [ ] 简化为核心方法：
  - [ ] detectConflicts(worktreePath: string) → ConflictInfo[]
  - [ ] hasConflicts(worktreePath: string) → boolean
  - [ ] getConflictLevel(conflicts: ConflictInfo[]) → 1 | 2 | 3
- [ ] 实现 Git 命令：
  - [ ] `git diff --name-only --diff-filter=U`
- [ ] 编写单元测试

#### TODO 3.3: 保留/爆改 TmuxController.ts
- [ ] 读取现有 `src/parallel/tmux/TmuxController.ts`
- [ ] 确保包含核心方法：
  - [ ] createSession(name: string, cwd: string) → void
  - [ ] killSession(name: string) → void
  - [ ] sendCommand(name: string, command: string) → void
  - [ ] captureOutput(name: string) → string
  - [ ] listSessions() → string[]
  - [ ] sessionExists(name: string) → boolean
- [ ] 实现 Tmux 命令：
  - [ ] `tmux new-session -d -s <name> -c <cwd>`
  - [ ] `tmux kill-session -t <name>`
  - [ ] `tmux send-keys -t <name> '<command>' Enter`
  - [ ] `tmux capture-pane -t <name> -p`
- [ ] 编写单元测试

#### TODO 3.4: 保留/爆改 SessionMonitor.ts
- [ ] 读取现有 `src/parallel/tmux/SessionMonitor.ts`
- [ ] 确保包含：
  - [ ] startMonitoring(sessionName: string, interval: number) → void
  - [ ] stopMonitoring(sessionName: string) → void
  - [ ] onOutput(callback: (output: string) => void) → void
  - [ ] isTaskCompleted(output: string) → boolean
- [ ] 实现 15 秒轮询逻辑
- [ ] 解析 Claude stream-json 输出
- [ ] 检测 `type: 'result'` 表示任务完成
- [ ] 编写单元测试

#### TODO 3.5: 爆改 TaskExecutor.ts
- [ ] 读取现有 `src/parallel/worker/TaskExecutor.ts`
- [ ] 实现核心方法：
  - [ ] executeTask(task: Task, worktreePath: string, tmuxSession: string) → void
  - [ ] buildClaudeCommand(task: Task) → string
- [ ] 构建 Claude Headless 命令：
  ```typescript
  `claude -p "${taskPrompt}" --output-format stream-json --permission-mode acceptEdits`
  ```
- [ ] 通过 TmuxController 发送命令
- [ ] 编写单元测试

**Phase 3 验收标准**：
- [ ] `WorktreeManager.create()` 能创建 worktree
- [ ] `TmuxController.createSession()` 能创建 tmux 会话
- [ ] `TmuxController.sendCommand()` 能发送命令
- [ ] `SessionMonitor` 能检测任务完成
- [ ] 端到端测试：创建 worktree → 创建 tmux → 执行命令

**🔍 Phase 3 验证（使用 Claude Task Agent）**：
```bash
claude task verify-phase --phase=3 --e2e-test
```
验证项：
- [ ] 运行 `npm test -- --grep="Worktree|Tmux|SessionMonitor"`
- [ ] 手动测试：`git worktree add` 命令
- [ ] 手动测试：`tmux new-session` 和 `tmux capture-pane`
- [ ] 验证 Claude Headless 命令构建

---

### Phase 4: Layer 4 通信层（爆改 Happy 代码）

**目标**：实现 Master-Worker Socket.IO 通信

#### TODO 4.1: 爆改 SocketClient.ts
- [ ] 读取 `src/parallel/communication/SocketClient.ts`（从 Phase 0 复制）
- [ ] 移除代码：
  - [ ] `import { TokenStorage } ...`
  - [ ] `import { Encryption } ...`
  - [ ] `private encryption: Encryption | null`
  - [ ] `sessionRPC()` 方法
  - [ ] `machineRPC()` 方法
  - [ ] `request()` 方法
  - [ ] `updateToken()` 方法
- [ ] 保留代码：
  - [ ] `io()` Socket.IO 连接
  - [ ] `connect()` / `disconnect()`
  - [ ] `onMessage()` / `send()`
  - [ ] `emitWithAck()`
  - [ ] `setupEventHandlers()`
  - [ ] `onStatusChange()` / `onReconnected()`
- [ ] 修改配置：
  - [ ] 简化 auth 配置
  - [ ] 修改 path 为 `/paralleldev`
- [ ] 编写单元测试

#### TODO 4.2: 创建 SocketServer.ts
- [ ] 创建 Master 端 Socket.IO 服务器
- [ ] 实现事件监听：
  - [ ] `on('worker:register', handler)` - Worker 注册
  - [ ] `on('worker:task_completed', handler)` - 任务完成
  - [ ] `on('worker:task_failed', handler)` - 任务失败
  - [ ] `on('worker:task_progress', handler)` - 任务进度
  - [ ] `on('worker:heartbeat', handler)` - 心跳
- [ ] 实现事件发送：
  - [ ] `emit('master:task_assign', data)` - 分配任务
  - [ ] `emit('master:task_cancel', data)` - 取消任务
  - [ ] `emit('master:worker_terminate', data)` - 终止 Worker
- [ ] 实现 Worker 管理：
  - [ ] 维护已连接 Worker 列表
  - [ ] 处理 Worker 断开连接
- [ ] 编写单元测试

#### TODO 4.3: 爆改 RpcManager.ts
- [ ] 读取 `src/parallel/communication/RpcManager.ts`（从 Phase 0 复制）
- [ ] 移除加密相关代码：
  - [ ] `encryptionKey`
  - [ ] `encryptionVariant`
  - [ ] `encrypt()` / `decrypt()` 调用
- [ ] 保留 RPC 模式：
  - [ ] `registerHandler(method, handler)`
  - [ ] `handleRequest(request)`
  - [ ] `onSocketConnect()` / `onSocketDisconnect()`
- [ ] 编写单元测试

#### TODO 4.4: 创建 MessageProtocol.ts
- [ ] 定义消息类型：
  ```typescript
  type WorkerEventType = 'register' | 'task_completed' | 'task_failed' | 'task_progress' | 'heartbeat';
  type MasterEventType = 'task_assign' | 'task_cancel' | 'worker_terminate';
  ```
- [ ] 定义消息结构：
  ```typescript
  interface WorkerEvent { type, workerId, taskId?, timestamp, payload? }
  interface MasterCommand { type, taskId?, task?, workerId? }
  ```
- [ ] 使用 Zod 定义消息验证

#### TODO 4.5: 爆改 StatusReporter.ts
- [ ] 读取现有 `src/parallel/worker/StatusReporter.ts`
- [ ] 基于 SocketClient 重写：
  - [ ] `reportTaskStarted(taskId)` → `socket.emit('worker:task_started', ...)`
  - [ ] `reportTaskCompleted(taskId, result)` → `socket.emit('worker:task_completed', ...)`
  - [ ] `reportTaskFailed(taskId, error)` → `socket.emit('worker:task_failed', ...)`
  - [ ] `reportTaskProgress(taskId, progress, message)` → `socket.emit('worker:task_progress', ...)`
  - [ ] `startHeartbeat(interval)` - 30秒心跳
- [ ] 编写单元测试

**Phase 4 验收标准**：
- [ ] SocketServer 能接收 Worker 连接
- [ ] SocketClient 能连接到 Server
- [ ] Worker 能通过 StatusReporter 上报状态
- [ ] 端到端测试：Worker 连接 → 上报状态 → Master 接收

**🔍 Phase 4 验证（使用 Claude Task Agent）**：
```bash
claude task verify-phase --phase=4 --socket-test
```
验证项：
- [ ] 运行 `npm test -- --grep="Socket|RPC|StatusReporter"`
- [ ] 启动 SocketServer 验证连接
- [ ] 发送测试消息验证通信
- [ ] 验证心跳机制（30秒间隔）

---

### Phase 5: Layer 2 编排层

**目标**：实现任务调度和 Worker 池管理

#### TODO 5.1: 爆改 StateManager.ts
- [ ] 读取现有 `src/parallel/master/StateManager.ts`
- [ ] 实现状态持久化：
  - [ ] `saveState()` - 保存到 `.paralleldev/state.json`
  - [ ] `loadState()` - 从 state.json 加载
  - [ ] `updateWorkerState(workerId, state)` - 更新 Worker 状态
  - [ ] `updateTaskState(taskId, state)` - 更新任务状态
- [ ] 实现状态查询：
  - [ ] `getWorkerState(workerId)` → WorkerState
  - [ ] `getTaskState(taskId)` → TaskState
  - [ ] `getAllWorkers()` → Worker[]
  - [ ] `getAllTasks()` → Task[]
- [ ] 编写单元测试

#### TODO 5.2: 爆改 WorkerPool.ts
- [ ] 读取现有 `src/parallel/master/WorkerPool.ts`
- [ ] 实现 Worker 管理：
  - [ ] `createWorker(id)` - 创建新 Worker
  - [ ] `removeWorker(id)` - 移除 Worker
  - [ ] `getIdleWorker()` → Worker | null
  - [ ] `getWorker(id)` → Worker | null
  - [ ] `getAllWorkers()` → Worker[]
- [ ] 实现 Worker 状态管理：
  - [ ] `markBusy(workerId, taskId)`
  - [ ] `markIdle(workerId)`
  - [ ] `markFailed(workerId, error)`
- [ ] 实现 Socket.IO 集成：
  - [ ] 监听 Worker 连接/断开
  - [ ] 处理心跳超时（90秒）
- [ ] 编写单元测试

#### TODO 5.3: 爆改 MasterOrchestrator.ts
- [ ] 读取现有 `src/parallel/master/MasterOrchestrator.ts`
- [ ] 实现核心调度循环（事件驱动）：
  ```typescript
  async start() {
    // 1. 启动 SocketServer
    // 2. 加载任务
    // 3. 创建 Worker 池
    // 4. 开始调度
  }
  ```
- [ ] 实现任务分配：
  - [ ] `assignNextTask()` - 获取可执行任务并分配
  - [ ] `onTaskCompleted(workerId, taskId, result)` - 处理任务完成
  - [ ] `onTaskFailed(workerId, taskId, error)` - 处理任务失败
  - [ ] `onWorkerDisconnected(workerId)` - 处理 Worker 断开
- [ ] 实现冲突检测和解决：
  - [ ] 任务完成后检测冲突
  - [ ] 调用 ConflictResolver
- [ ] 实现质量检查：
  - [ ] 任务完成后运行质量检查
  - [ ] 调用 CodeValidator
- [ ] 编写单元测试

**Phase 5 验收标准**：
- [ ] StateManager 能持久化和恢复状态
- [ ] WorkerPool 能管理 Worker 生命周期
- [ ] MasterOrchestrator 能完成调度循环
- [ ] 端到端测试：启动 → 分配任务 → 任务完成 → 下一个任务

**🔍 Phase 5 验证（使用 Claude Task Agent）**：
```bash
claude task verify-phase --phase=5 --integration-test
```
验证项：
- [ ] 运行 `npm test -- --grep="State|Worker|Orchestrator"`
- [ ] 验证状态文件 `.paralleldev/state.json` 正确保存
- [ ] 验证 Worker 池创建和管理
- [ ] 运行完整调度循环测试（2 个简单任务）

---

### Phase 6: Layer 5 质量保证

**目标**：实现代码验证和冲突解决

#### TODO 6.1: 创建 SubagentRunner.ts
- [ ] 实现 Subagent 执行器：
  - [ ] `runSubagent(agentName, context)` → SubagentResult
  - [ ] 支持调用 `.claude/agents/` 下的 Subagent
- [ ] 实现输出解析
- [ ] 编写单元测试

#### TODO 6.2: 爆改 CodeValidator.ts
- [ ] 读取现有 `src/parallel/quality/CodeValidator.ts`
- [ ] 实现质量检查：
  - [ ] `validateCode(worktreePath)` → ValidationResult
  - [ ] `runTypeCheck(worktreePath)` → boolean
  - [ ] `runLint(worktreePath)` → LintResult
  - [ ] `runTests(worktreePath)` → TestResult
- [ ] 集成 Subagent（可选）：
  - [ ] 调用 quality-gate Subagent
- [ ] 编写单元测试

#### TODO 6.3: 爆改 ConflictResolver.ts
- [ ] 读取现有 `src/parallel/git/ConflictResolver.ts`
- [ ] 实现分层解决：
  - [ ] `resolveConflicts(worktreePath)` → ResolutionResult
  - [ ] `autoResolve(conflicts)` - Level 1 自动解决
  - [ ] `aiAssistedResolve(conflicts)` - Level 2 AI 辅助
  - [ ] `requestHumanIntervention(conflicts)` - Level 3 人工介入
- [ ] 集成 Subagent：
  - [ ] 调用 conflict-resolver Subagent
- [ ] 编写单元测试

**Phase 6 验收标准**：
- [ ] CodeValidator 能运行质量检查
- [ ] ConflictResolver 能处理冲突
- [ ] Subagent 集成工作正常

**🔍 Phase 6 验证（使用 Claude Task Agent）**：
```bash
claude task verify-phase --phase=6 --quality-check
```
验证项：
- [ ] 运行 `npm test -- --grep="CodeValidator|ConflictResolver|Subagent"`
- [ ] 测试 TypeScript 类型检查集成
- [ ] 测试 ESLint 检查集成
- [ ] 测试 Git 冲突检测和分层解决

---

### Phase 7: Layer 6 通知层

**目标**：实现通知和报告生成

#### TODO 7.1: 爆改 NotificationManager.ts
- [ ] 读取现有 `src/parallel/notification/NotificationManager.ts`
- [ ] 实现通知方法：
  - [ ] `notifyTaskCompleted(taskId, result)`
  - [ ] `notifyTaskFailed(taskId, error)`
  - [ ] `notifyAllCompleted(report)`
  - [ ] `notifyConflictDetected(taskId, conflicts)`
- [ ] 实现通知渠道：
  - [ ] 终端输出（console.log with emoji）
  - [ ] 系统声音（可选）
- [ ] 编写单元测试

#### TODO 7.2: 爆改 ReportGenerator.ts
- [ ] 读取现有 `src/parallel/notification/ReportGenerator.ts`
- [ ] 实现报告生成：
  - [ ] `generateReport(state)` → Report
  - [ ] `formatReport(report)` → string
- [ ] 报告内容：
  - [ ] 总任务数、完成数、失败数
  - [ ] 总耗时
  - [ ] 每个任务的详情
  - [ ] 冲突解决情况
- [ ] 编写单元测试

**Phase 7 验收标准**：
- [ ] 任务完成时有通知
- [ ] 所有任务完成后生成报告

**🔍 Phase 7 验证（使用 Claude Task Agent）**：
```bash
claude task verify-phase --phase=7 --notification-test
```
验证项：
- [ ] 运行 `npm test -- --grep="Notification|Report"`
- [ ] 测试终端通知输出（emoji + 颜色）
- [ ] 测试报告生成格式
- [ ] 验证报告内容完整性

---

### Phase 8: CLI 和集成测试

**目标**：实现 CLI 命令和完整测试

#### TODO 8.1: 爆改 cli-parallel.ts
- [ ] 读取现有 `src/cli-parallel.ts`
- [ ] 实现 CLI 命令：
  ```bash
  paralleldev task list          # 列出任务
  paralleldev task show <id>     # 显示任务详情
  paralleldev run --workers 3    # 启动并行执行
  paralleldev status             # 查看运行状态
  paralleldev report             # 生成报告
  paralleldev clean              # 清理 worktree 和 tmux
  ```
- [ ] 使用 commander.js 或 yargs
- [ ] 实现参数验证
- [ ] 实现帮助信息

#### TODO 8.2: 编写集成测试
- [ ] 测试 1：任务加载和 DAG 构建
- [ ] 测试 2：Worker 创建和 Socket.IO 通信
- [ ] 测试 3：Worktree 创建和 Tmux 会话
- [ ] 测试 4：完整调度循环（2-3 个简单任务）
- [ ] 测试 5：错误恢复（Worker 崩溃）

#### TODO 8.3: 端到端测试
- [ ] 准备测试任务文件 `.taskmaster/tasks/tasks.json`
- [ ] 运行 `paralleldev run --workers 2`
- [ ] 验证所有任务完成
- [ ] 验证报告生成

**Phase 8 验收标准**：
- [ ] CLI 命令可用
- [ ] 集成测试全部通过
- [ ] 端到端测试成功：2-3 个简单任务并行执行完成

**🔍 Phase 8 验证（使用 Claude Task Agent）**：
```bash
claude task verify-phase --phase=8 --full-e2e
```
验证项：
- [ ] 运行 `paralleldev --help` 验证 CLI
- [ ] 运行 `npm run test:integration` 全部通过
- [ ] 端到端测试：`paralleldev run --workers 2`
- [ ] 验证所有任务完成并生成报告

---

### 验收标准汇总

#### MVP 验收（Phase 0-5 完成后）
- [ ] 能够加载 `.taskmaster/tasks/tasks.json`
- [ ] 能够创建 3 个 Worker
- [ ] 能够并行执行无依赖任务
- [ ] Socket.IO 通信正常（Worker 上报、Master 分配）
- [ ] 任务完成后自动调度下一个
- [ ] Tmux 会话正常工作

#### 完整验收（所有 Phase 完成后）
- [ ] 冲突检测和解决
- [ ] 质量检查（Lint/TypeCheck）
- [ ] 通知和报告
- [ ] 错误恢复（Worker 崩溃重试）
- [ ] CLI 命令完整可用
- [ ] 80%+ 测试覆盖率

---

## 九、完整文件清单

### TypeScript 源文件（16 个）

| 文件路径 | 层级 | 职责 |
|---------|------|------|
| `src/parallel/types.ts` | - | 核心类型定义 |
| `src/parallel/config.ts` | - | 配置管理 |
| `src/parallel/index.ts` | - | 模块导出 |
| `src/parallel/task/TaskDAG.ts` | L1 | 任务依赖图 |
| `src/parallel/task/TaskScheduler.ts` | L1 | 任务调度 |
| `src/parallel/task/TaskManager.ts` | L1 | 自定义任务管理器 |
| `src/parallel/master/MasterOrchestrator.ts` | L2 | 主编排器 |
| `src/parallel/master/WorkerPool.ts` | L2 | Worker 池 |
| `src/parallel/master/StateManager.ts` | L2 | 状态管理 |
| `src/parallel/execution/WorktreeManager.ts` | L3 | Worktree 管理 |
| `src/parallel/execution/ClaudeHeadless.ts` | L3 | Claude Headless 模式 |
| `src/parallel/worker/StatusReporter.ts` | L4 | Worker 状态上报 |
| `src/parallel/communication/SocketServer.ts` | L4 | Socket 服务器 |
| `src/parallel/communication/MessageProtocol.ts` | L4 | 消息协议 |
| `src/parallel/quality/SubagentRunner.ts` | L5 | Subagent 执行器 |
| `src/parallel/quality/CodeValidator.ts` | L5 | 代码验证 |
| `src/parallel/quality/ConflictResolver.ts` | L5 | 冲突解决 |
| `src/parallel/notification/NotificationManager.ts` | L6 | 通知管理 |
| `src/parallel/notification/ReportGenerator.ts` | L6 | 报告生成 |
| `src/cli-parallel.ts` | - | CLI 入口 |

### 任务配置文件
| 文件路径 | 职责 |
|---------|------|
| `.paralleldev/tasks.json` | 任务定义 |
| `.paralleldev/state.json` | 运行状态 |
| `.paralleldev/config.json` | 项目配置 |

### Claude Code Plugin 文件清单

#### Plugin 元数据（1 个）
| 文件路径 | 职责 |
|---------|------|
| `paralleldev-plugin/.claude-plugin/plugin.json` | Plugin 配置和元数据 |

#### 斜杠命令（5 个）
| 文件路径 | 命令 | 职责 |
|---------|------|------|
| `paralleldev-plugin/commands/start.md` | /pd:start | 启动并行执行系统 |
| `paralleldev-plugin/commands/status.md` | /pd:status | 查看运行状态 |
| `paralleldev-plugin/commands/assign.md` | /pd:assign | 手动分配任务 |
| `paralleldev-plugin/commands/stop.md` | /pd:stop | 停止执行 |
| `paralleldev-plugin/commands/report.md` | /pd:report | 生成报告 |

#### Agents（4 个）
| 文件路径 | 职责 |
|---------|------|
| `paralleldev-plugin/agents/task-orchestrator.md` | 任务编排专家（依赖分析、执行规划） |
| `paralleldev-plugin/agents/quality-gate.md` | 质量门禁专家（TypeScript、ESLint、测试） |
| `paralleldev-plugin/agents/conflict-resolver.md` | 冲突解决专家（分层策略） |
| `paralleldev-plugin/agents/worker-monitor.md` | Worker 监控专家（健康检查） |

#### Skills（7 个目录，共 23 个文件）
| Skill | 文件 | 职责 |
|-------|------|------|
| **parallel-executor** | `SKILL.md`, `WORKFLOW.md`, 2 脚本 | 并行任务执行能力 |
| **conflict-resolution** | `SKILL.md`, `STRATEGIES.md`, 1 脚本 | 冲突解决能力 |
| **quality-assurance** | `SKILL.md`, `CHECKS.md`, 3 脚本 | 质量保证能力 |
| **frontend-development** | `SKILL.md`, `RULES.md`, `TEMPLATES.md` | 前端开发规范（React/Vue/Nuxt3）|
| **go-development** | `SKILL.md`, `RULES.md`, `TEMPLATES.md` | Go 开发规范（Go 1.23+/Gin/GORM）|
| **java-development** | `SKILL.md`, `RULES.md`, `TEMPLATES.md` | Java 开发规范（JDK 17+）|
| **typescript-development** | `SKILL.md`, `RULES.md`, `TEMPLATES.md` | TypeScript 后端开发规范 |

#### Hooks 和 MCP（2 个）
| 文件路径 | 职责 |
|---------|------|
| `paralleldev-plugin/hooks/hooks.json` | 事件处理（PostToolUse, Stop） |
| `paralleldev-plugin/.mcp.json` | MCP 服务器配置 |

#### 支持脚本（5 个）
| 文件路径 | 职责 |
|---------|------|
| `paralleldev-plugin/scripts/master-start.sh` | 启动 Master 进程 |
| `paralleldev-plugin/scripts/worker-start.sh` | 启动 Worker 进程 |
| `paralleldev-plugin/scripts/cleanup.sh` | 清理所有资源 |
| `paralleldev-plugin/scripts/notify-change.sh` | 文件变更通知 |
| `paralleldev-plugin/scripts/task-completed.sh` | 任务完成通知 |

#### 项目配置（1 个）
| 文件路径 | 职责 |
|---------|------|
| `.claude/settings.json` | 项目设置（启用 plugin） |

**Plugin 文件总计**：40 个文件（原 28 个 + 语言 Skills 12 个）

---

## 八、代码规范要求

### 遵循 CLAUDE.md 规范

1. **函数长度**：不超过 50 行
2. **类型安全**：禁止 `any`，使用 Zod 验证
3. **错误处理**：所有异步操作 try-catch
4. **注释**：JSDoc + 步骤注释
5. **命名**：
   - 接口：`PascalCase`
   - 函数：`camelCase`
   - 常量：`UPPER_SNAKE_CASE`
6. **导入**：使用 `@/` 别名

### 文件模板

```typescript
/**
 * @fileoverview [文件描述]
 * @layer [Layer X: Name]
 */

import { z } from 'zod';

// ============================================================
// Types
// ============================================================

export interface SomeInterface {
  // ...
}

// ============================================================
// Constants
// ============================================================

const SOME_CONSTANT = 'value';

// ============================================================
// Implementation
// ============================================================

/**
 * [函数描述]
 * @param param - [参数描述]
 * @returns [返回值描述]
 */
export async function someFunction(param: string): Promise<void> {
  // 1. 步骤一
  // 2. 步骤二
}
```

---

## 九、验证标准

### MVP 验证（Phase 1-5 完成后）

- [ ] 能够加载 tasks.json
- [ ] 能够创建 3 个 Worker
- [ ] 能够并行执行无依赖任务
- [ ] Socket.IO 通信正常
- [ ] 任务完成后自动调度下一个

### 完整验证（所有 Phase 完成后）

- [ ] 冲突检测和解决
- [ ] 质量检查（Lint/TypeCheck/Test）
- [ ] 通知和报告
- [ ] 错误恢复
- [ ] 80%+ 测试覆盖率

---

## 十、风险评估

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| Claude Code SDK 变更 | 低 | 封装在 ClaudeExecutor 中 |
| Socket.IO 连接不稳定 | 低 | 内置重连 + 心跳检测 |
| Worktree 冲突 | 中 | 分层冲突解决策略 |
| Tmux 会话管理复杂 | 低 | 封装在 TmuxController 中 |
| 任务依赖死锁 | 低 | DAG 拓扑排序验证 |

---

## 十三、总结

### 🔴 核心策略：Pull 代码 → 爆改

**用户明确要求**："我希望是 pull taskmaster 的代码，然后开始去爆改。而是不会简单的自己实现。Happy 风格通信 我希望的也是如此"

### Pull 代码清单

| 来源 | 源文件 | 目标文件 | 爆改内容 |
|-----|-------|---------|---------|
| **task-master GitHub** | `packages/*/src/*dag*.ts` | `task/TaskDAG.ts` | 完全保留 |
| **task-master GitHub** | `packages/*/src/*scheduler*.ts` | `task/TaskScheduler.ts` | 简化策略 |
| **Happy 项目** | `happy/sources/sync/apiSocket.ts` | `communication/SocketClient.ts` | 移除加密/认证 |
| **本项目** | `src/api/rpc/RpcHandlerManager.ts` | `communication/RpcManager.ts` | 简化加密 |
| **本项目** | `src/parallel/task/TaskMasterAdapter.ts` | `task/TaskManager.ts` | 重命名 + 简化 |

### 爆改策略优势

1. **Pull 而非重写** - 复用经过验证的代码，减少 bug
2. **保留核心能力** - Tmux（进程隔离）+ TaskDAG（依赖图）完全保留
3. **简化复杂度** - 移除过度设计，保持 YAGNI 原则
4. **事件驱动** - Socket.IO + StatusReporter 即时通知（Happy 风格）
5. **Tmux 核心能力** - 确保只有无依赖任务才能并行执行

### 爆改对照表

| 原始代码 | 爆改后 | 保留 | 移除 |
|---------|-------|------|------|
| `apiSocket.ts` (262行) | `SocketClient.ts` (~150行) | 连接管理、emit、事件处理 | 加密、认证、HTTP |
| `RpcHandlerManager.ts` (135行) | `RpcManager.ts` (~80行) | RPC 注册/调用 | 加密 |
| task-master TaskDAG | `TaskDAG.ts` | 依赖图、拓扑排序 | - |
| task-master TaskScheduler | `TaskScheduler.ts` (~100行) | PRIORITY_FIRST | LOAD_BALANCED |
| `TaskMasterAdapter.ts` (168行) | `TaskManager.ts` (~100行) | 加载/保存/验证 | 复杂序列化 |

### 关键架构决策

```
设计决策                      选择方案
────────────────────────────────────────────
代码来源                      Pull 代码 + 爆改 ✅
                             而非从零实现 ❌

任务完成通知                  Socket.IO emit（Pull Happy 代码）✅
                             而非 Claude Code Stop Hook ❌

任务管理系统                  Pull task-master.dev 代码 + 爆改 ✅
                             保留 tasks.json 格式
                             简化复杂度

执行隔离                      Tmux 会话（保留）✅
                             + Git Worktree（保留）✅
                             + Claude Headless（在 Tmux 中执行）

并行控制                      TaskDAG.getReadyTasks() ✅
                             只有依赖已满足的任务才能并行
```

### Claude Code 2025 能力利用

| 能力 | 应用场景 |
|-----|---------|
| **Headless 模式** | `claude -p` 在 Tmux 会话中执行 |
| **stream-json** | 通过 Tmux capture-pane 捕获输出 |
| **Plugin 系统** | 打包命令、Agents、Skills、Hooks 为可分发的扩展包 |
| **Custom Agents** | task-orchestrator, quality-gate, conflict-resolver, worker-monitor |
| **Skills** | parallel-executor, conflict-resolution, quality-assurance |
| **Hooks** | PostToolUse（监控文件变更）, Stop（任务完成通知） |
| **MCP Server** | paralleldev-master 用于 Master-Worker 通信 |

### Plugin 架构优势

```
┌─────────────────────────────────────────────────────────────┐
│               Claude Code Plugin 架构                        │
└─────────────────────────────────────────────────────────────┘

paralleldev-plugin/
├── .claude-plugin/plugin.json    # Plugin 元数据
├── commands/                      # 斜杠命令 (/pd:start, /pd:status, ...)
│   └── 5 个命令文件
├── agents/                        # 4 个子智能体
│   ├── task-orchestrator.md      # 任务编排专家
│   ├── quality-gate.md           # 质量门禁专家
│   ├── conflict-resolver.md      # 冲突解决专家
│   └── worker-monitor.md         # Worker 监控专家
├── skills/                        # 3 个能力扩展
│   ├── parallel-executor/        # 并行执行能力
│   ├── conflict-resolution/      # 冲突解决能力
│   └── quality-assurance/        # 质量保证能力
├── hooks/hooks.json               # 事件处理
├── .mcp.json                      # MCP 服务器配置
└── scripts/                       # 支持脚本
```

**Plugin 优势**：
1. **团队共享** - 通过 Marketplace 分发
2. **版本管理** - Semantic versioning
3. **统一配置** - 命令、Agents、Skills、Hooks 一体化
4. **跨项目复用** - 安装即用

### 文件变化统计

| 类别 | 现有 | 爆改后 | 变化 |
|-----|------|-------|-----|
| **保留文件** | - | 5 个 | TaskDAG, TmuxController, SessionMonitor 等 |
| **爆改文件** | - | 12 个 | 简化复杂度，保留核心功能 |
| **删除文件** | - | 6 个 | 移除冗余/过时代码 |
| **新增 TypeScript** | - | 16 个 | 核心模块 |
| **新增 Plugin 文件** | - | 28 个 | 命令、Agents、Skills、Hooks、脚本 |
| **预计代码量** | ~7,318 行 | ~5,000 行 | -32% |

### 核心改进

```
┌─────────────────────────────────────────────────────────────┐
│                     爆改核心改进                             │
└─────────────────────────────────────────────────────────────┘

1. Tmux 核心能力保留
   ├─ 进程隔离：每个 Worker 独立 tmux 会话
   ├─ 输出捕获：capture-pane 获取 Claude 输出
   ├─ 会话持久化：断开后可重连
   └─ 无依赖并行：只有 ready 任务才能并行

2. Task Master 爆改简化
   ├─ 保留 .taskmaster/tasks/tasks.json 格式
   ├─ 保留 TaskDAG 依赖图
   ├─ 简化 TaskScheduler 调度策略
   └─ 重命名 TaskMasterAdapter → TaskManager

3. Happy 风格通信
   ├─ Socket.IO 双向通信
   ├─ StatusReporter 主动上报
   └─ 事件驱动，非轮询

4. Claude Code Plugin 架构（新增）
   ├─ 统一打包：命令 + Agents + Skills + Hooks + MCP
   ├─ 斜杠命令：/pd:start, /pd:status, /pd:stop 等
   ├─ 4 个专业 Agents：
   │   ├─ task-orchestrator（任务编排）
   │   ├─ quality-gate（质量门禁）
   │   ├─ conflict-resolver（冲突解决）
   │   └─ worker-monitor（监控）
   ├─ 7 个 Skills（含 4 个语言规范 Skills）：
   │   ├─ parallel-executor（并行执行）
   │   ├─ conflict-resolution（冲突解决）
   │   ├─ quality-assurance（质量保证）
   │   ├─ frontend-development（前端规范）← 新增
   │   ├─ go-development（Go 规范）← 新增
   │   ├─ java-development（Java 规范）← 新增
   │   └─ typescript-development（TypeScript 规范）← 新增
   ├─ Hooks 事件处理：
   │   ├─ PostToolUse（文件变更监控）
   │   └─ Stop（任务完成通知）
   └─ MCP 服务器集成
```
