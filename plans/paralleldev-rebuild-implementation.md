# ParallelDev 从零重建 - 完整实施计划

> 严格遵循 `polymorphic-wandering-leaf.md` 规范 + README.md 6 层架构

## 核心目标

1. **严格遵循 README.md 的 6 层架构设计**
2. **最大化利用 Claude Code 2025 新能力**（Headless、Subagent、Skills）
3. **Pull Happy 的 Socket.IO + RPC 代码并爆改**
4. **Pull task-master.dev 源码并爆改**（不是自己实现）
5. 事件驱动，无轮询
6. YAGNI 原则，最小可用

## Task Master 爆改要求

1. **保留** `.taskmaster/tasks/tasks.json` 格式
2. **保留** TaskDAG 依赖图
3. **保留** TaskScheduler 调度策略（PRIORITY_FIRST + DEPENDENCY_FIRST）
4. **重命名** TaskMasterAdapter → TaskManager

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

**记录需要参考的文件列表**（执行后更新）：
- TaskDAG 实现: `./claude-task-master/src/???`
- TaskScheduler 实现: `./claude-task-master/src/???`
- 任务类型定义: `./claude-task-master/src/???`
- tasks.json 格式定义: `./claude-task-master/.taskmaster/???`

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.3: 复制 task-master 核心文件

**步骤**：
```bash
# 0.3.1 创建目标目录
mkdir -p src/parallel/task

# 0.3.2 复制 TaskDAG 相关文件（路径根据 0.2 分析结果填写）
# cp ./claude-task-master/src/path/to/dag.ts src/parallel/task/TaskDAG.ts

# 0.3.3 复制 TaskScheduler 相关文件
# cp ./claude-task-master/src/path/to/scheduler.ts src/parallel/task/TaskScheduler.ts

# 0.3.4 复制类型定义
# cp ./claude-task-master/src/path/to/types.ts src/parallel/task/task-types.ts

# 0.3.5 验证复制结果
ls -la src/parallel/task/
```
**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.4: 复制 Happy Socket.IO 客户端代码

**步骤**：
```bash
# 0.4.1 创建目标目录
mkdir -p src/parallel/communication

# 0.4.2 检查 Happy 源文件是否存在
ls -la happy/sources/sync/apiSocket.ts 2>/dev/null || echo "文件不存在，需要从 Happy 仓库获取"

# 0.4.3 复制文件（如果存在）
cp happy/sources/sync/apiSocket.ts src/parallel/communication/SocketClient.ts

# 0.4.4 记录需要移除的代码段
# - encrypt() / decrypt() 相关
# - TokenStorage 认证相关
# - HTTP request 方法
```

**需要移除的代码段**：
- `import { encrypt, decrypt } from '...'`
- `TokenStorage` 相关
- `sessionRPC()` / `machineRPC()` 中的认证逻辑

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.5: 复制 RPC 管理器代码

**步骤**：
```bash
# 0.5.1 检查源文件
ls -la src/api/rpc/RpcHandlerManager.ts 2>/dev/null || ls -la happy/src/api/rpc/RpcHandlerManager.ts

# 0.5.2 复制文件
cp src/api/rpc/RpcHandlerManager.ts src/parallel/communication/RpcManager.ts 2>/dev/null || \
cp happy/src/api/rpc/RpcHandlerManager.ts src/parallel/communication/RpcManager.ts

# 0.5.3 验证
cat src/parallel/communication/RpcManager.ts | head -30
```

**需要移除的代码段**：
- 加密逻辑
- 复杂的认证流程

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 0.6: 复制 RPC 类型定义

**步骤**：
```bash
# 0.6.1 复制类型定义
cp src/api/rpc/types.ts src/parallel/communication/rpc-types.ts 2>/dev/null || \
cp happy/src/api/rpc/types.ts src/parallel/communication/rpc-types.ts

# 0.6.2 验证目录结构
ls -la src/parallel/communication/
# 期望看到:
# - SocketClient.ts
# - RpcManager.ts
# - rpc-types.ts
```
**完成后**：task agent 自测 → 询问是否提交推送

**Phase 0 验收标准**：
- [ ] `./claude-task-master` 目录存在且包含源码
- [ ] `src/parallel/task/` 目录存在
- [ ] `src/parallel/communication/SocketClient.ts` 存在
- [ ] `src/parallel/communication/RpcManager.ts` 存在
- [ ] `src/parallel/communication/rpc-types.ts` 存在

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

**📄 package.json 完整模板**：
```json
{
  "name": "parallel-dev-mcp",
  "version": "1.0.0",
  "description": "Claude Code 自动化并行开发系统",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "dev": "tsc -w",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint src --ext .ts",
    "typecheck": "tsc --noEmit",
    "clean": "rm -rf dist"
  },
  "dependencies": {
    "socket.io": "^4.7.0",
    "socket.io-client": "^4.7.0",
    "zod": "^3.22.0",
    "commander": "^11.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.3.0",
    "vitest": "^1.0.0",
    "eslint": "^8.50.0",
    "@typescript-eslint/parser": "^6.0.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0"
  },
  "engines": {
    "node": ">=20.0.0"
  }
}
```

**📄 tsconfig.json 完整模板**：
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "paths": {
      "@/*": ["./src/*"]
    },
    "baseUrl": "."
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

**📄 vitest.config.ts 完整模板**：
```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'dist/']
    }
  }
});
```

**📄 .gitignore 完整模板**：
```
node_modules/
dist/
.paralleldev/state.json
.worktrees/
*.log
.DS_Store
coverage/
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

**📄 src/parallel/types.ts 完整模板**：
```typescript
/**
 * ParallelDev 核心类型定义
 * @module parallel/types
 */

import { z } from 'zod';

// ============================================
// 任务相关类型
// ============================================

/** 任务状态 */
export type TaskStatus =
  | 'pending'     // 等待执行
  | 'ready'       // 依赖已满足，可执行
  | 'running'     // 正在执行
  | 'completed'   // 已完成
  | 'failed'      // 已失败
  | 'cancelled';  // 已取消

/** 任务定义 */
export interface Task {
  /** 任务唯一标识 */
  id: string;
  /** 任务标题 */
  title: string;
  /** 任务详细描述 */
  description: string;
  /** 依赖的任务 ID 列表 */
  dependencies: string[];
  /** 优先级 (1-5, 1最高) */
  priority: number;
  /** 当前状态 */
  status: TaskStatus;
  /** 分配的 Worker ID */
  assignedWorker?: string;
  /** 创建时间 (ISO 8601) */
  createdAt: string;
  /** 开始执行时间 */
  startedAt?: string;
  /** 完成时间 */
  completedAt?: string;
  /** 错误信息 */
  error?: string;
  /** 预估工时（小时） */
  estimatedHours?: number;
}

/** 任务 Zod Schema（运行时验证） */
export const TaskSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  description: z.string(),
  status: z.enum(['pending', 'ready', 'running', 'completed', 'failed', 'cancelled']),
  dependencies: z.array(z.string()),
  priority: z.number().min(1).max(5).default(3),
  assignedWorker: z.string().optional(),
  createdAt: z.string().datetime().optional(),
  startedAt: z.string().datetime().optional(),
  completedAt: z.string().datetime().optional(),
  error: z.string().optional(),
  estimatedHours: z.number().positive().optional()
});

/** tasks.json 文件 Schema */
export const TasksFileSchema = z.object({
  tasks: z.array(TaskSchema),
  meta: z.object({
    generatedAt: z.string().datetime(),
    projectName: z.string().optional(),
    version: z.string().optional()
  }).optional()
});

// ============================================
// Worker 相关类型
// ============================================

/** Worker 状态 */
export type WorkerStatus =
  | 'idle'      // 空闲
  | 'busy'      // 忙碌
  | 'error'     // 错误
  | 'offline';  // 离线

/** Worker 定义 */
export interface Worker {
  /** Worker 唯一标识 */
  id: string;
  /** 当前状态 */
  status: WorkerStatus;
  /** Git Worktree 路径 */
  worktreePath: string;
  /** Tmux 会话名称 */
  tmuxSession: string;
  /** 当前执行的任务 ID */
  currentTaskId?: string;
  /** 最后心跳时间 (ISO 8601) */
  lastHeartbeat: string;
  /** 已完成任务数 */
  completedTasks: number;
  /** 失败任务数 */
  failedTasks: number;
}

// ============================================
// 调度相关类型
// ============================================

/** 调度策略 */
export type SchedulingStrategy =
  | 'priority_first'    // 高优先级优先
  | 'dependency_first'; // 解除更多依赖的任务优先

/** 任务分配结果 */
export interface TaskAssignment {
  task: Task;
  worker: Worker;
  assignedAt: string;
}

/** 调度器统计 */
export interface SchedulerStats {
  totalTasks: number;
  pendingTasks: number;
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
  activeWorkers: number;
  idleWorkers: number;
}

// ============================================
// 通信相关类型（Socket.IO 事件）
// ============================================

/** Worker → Master 事件类型 */
export type WorkerEventType =
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'heartbeat'
  | 'progress';

/** Worker 事件 */
export interface WorkerEvent {
  type: WorkerEventType;
  workerId: string;
  taskId?: string;
  timestamp: string;
  payload?: {
    output?: string;
    error?: string;
    progress?: number;
    message?: string;
  };
}

/** Master → Worker 命令类型 */
export type MasterCommandType =
  | 'task_assign'
  | 'task_cancel'
  | 'worker_terminate';

/** Master 命令 */
export interface MasterCommand {
  type: MasterCommandType;
  taskId?: string;
  task?: Task;
  timestamp: string;
}

// ============================================
// 质量保证相关类型
// ============================================

/** 冲突级别 */
export type ConflictLevel = 1 | 2 | 3;
// Level 1: 自动解决（lockfiles, 格式化）
// Level 2: AI 辅助解决
// Level 3: 需要人工介入

/** 冲突信息 */
export interface ConflictInfo {
  file: string;
  level: ConflictLevel;
  conflictMarkers: string[];
  suggestedResolution?: string;
}

/** 解决结果 */
export interface ResolveResult {
  resolved: boolean;
  level?: ConflictLevel;
  conflicts?: string[];
  message?: string;
}

/** 任务执行结果 */
export interface TaskResult {
  success: boolean;
  output?: string;
  error?: string;
  duration?: number;
  filesChanged?: string[];
}

// ============================================
// 配置相关类型
// ============================================

/** 配置接口 */
export interface ParallelDevConfig {
  /** 最大 Worker 数量 */
  maxWorkers: number;
  /** Worktree 目录 */
  worktreeDir: string;
  /** 主分支名称 */
  mainBranch: string;
  /** Socket 服务端口 */
  socketPort: number;
  /** 心跳间隔（毫秒） */
  heartbeatInterval: number;
  /** 任务超时时间（毫秒） */
  taskTimeout: number;
  /** 调度策略 */
  schedulingStrategy: SchedulingStrategy;
}
```

**完成后**：task agent 自测（tsc --noEmit）→ 询问是否提交推送

### TODO 1.3: 创建 config.ts

**步骤**：
```bash
# 1.3.1 创建 config.ts 文件
# 1.3.2 运行 tsc --noEmit 验证
```

**📄 src/parallel/config.ts 完整模板**：
```typescript
/**
 * ParallelDev 配置管理
 * @module parallel/config
 */

import * as fs from 'fs';
import * as path from 'path';
import { ParallelDevConfig, SchedulingStrategy } from './types';

/** 默认配置 */
export const DEFAULT_CONFIG: ParallelDevConfig = {
  maxWorkers: 3,
  worktreeDir: '.worktrees',
  mainBranch: 'main',
  socketPort: 3001,
  heartbeatInterval: 30000,    // 30秒
  taskTimeout: 600000,         // 10分钟
  schedulingStrategy: 'priority_first'
};

/** 配置文件路径 */
const CONFIG_FILE = '.paralleldev/config.json';

/**
 * 加载配置
 * @param projectRoot 项目根目录
 * @returns 合并后的配置
 */
export function loadConfig(projectRoot: string): ParallelDevConfig {
  const configPath = path.join(projectRoot, CONFIG_FILE);

  if (!fs.existsSync(configPath)) {
    return { ...DEFAULT_CONFIG };
  }

  try {
    const fileContent = fs.readFileSync(configPath, 'utf-8');
    const userConfig = JSON.parse(fileContent);
    return { ...DEFAULT_CONFIG, ...userConfig };
  } catch (error) {
    console.warn(`⚠️  配置文件读取失败，使用默认配置: ${error}`);
    return { ...DEFAULT_CONFIG };
  }
}

/**
 * 保存配置
 * @param projectRoot 项目根目录
 * @param config 配置对象
 */
export function saveConfig(
  projectRoot: string,
  config: Partial<ParallelDevConfig>
): void {
  const configDir = path.join(projectRoot, '.paralleldev');
  const configPath = path.join(configDir, 'config.json');

  // 确保目录存在
  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
  }

  const fullConfig = { ...DEFAULT_CONFIG, ...config };
  fs.writeFileSync(configPath, JSON.stringify(fullConfig, null, 2));
}

/**
 * 验证配置有效性
 * @param config 配置对象
 * @returns 验证结果
 */
export function validateConfig(config: ParallelDevConfig): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  if (config.maxWorkers < 1 || config.maxWorkers > 10) {
    errors.push('maxWorkers 必须在 1-10 之间');
  }

  if (config.socketPort < 1024 || config.socketPort > 65535) {
    errors.push('socketPort 必须在 1024-65535 之间');
  }

  if (config.heartbeatInterval < 5000) {
    errors.push('heartbeatInterval 不能小于 5000ms');
  }

  if (config.taskTimeout < 60000) {
    errors.push('taskTimeout 不能小于 60000ms (1分钟)');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}
```

**完成后**：task agent 自测（tsc --noEmit）→ 询问是否提交推送

### TODO 1.4: 创建 index.ts

**步骤**：
```bash
# 1.4.1 创建 index.ts 模块导出文件
```

**📄 src/parallel/index.ts 完整模板**：
```typescript
/**
 * ParallelDev 模块导出
 * @module parallel
 */

// 类型导出
export * from './types';

// 配置导出
export { DEFAULT_CONFIG, loadConfig, saveConfig, validateConfig } from './config';

// Layer 1: Task Management
export { TaskDAG } from './task/TaskDAG';
export { TaskScheduler } from './task/TaskScheduler';
export { TaskManager } from './task/TaskManager';

// Layer 2: Orchestration (后续 Phase 实现)
// export { MasterOrchestrator } from './master/MasterOrchestrator';
// export { WorkerPool } from './master/WorkerPool';
// export { StateManager } from './master/StateManager';

// Layer 3: Execution (后续 Phase 实现)
// export { WorktreeManager } from './git/WorktreeManager';
// export { TmuxController } from './tmux/TmuxController';
// export { TaskExecutor } from './worker/TaskExecutor';

// Layer 4: Communication (后续 Phase 实现)
// export { SocketServer } from './communication/SocketServer';
// export { SocketClient } from './communication/SocketClient';
// export { StatusReporter } from './worker/StatusReporter';

// Layer 5: Quality Assurance (后续 Phase 实现)
// export { ConflictResolver } from './quality/ConflictResolver';
// export { CodeValidator } from './quality/CodeValidator';

// Layer 6: Notification (后续 Phase 实现)
// export { NotificationManager } from './notification/NotificationManager';
// export { ReportGenerator } from './notification/ReportGenerator';
```

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

**📄 .paralleldev/state.json 模板**：
```json
{
  "workers": [],
  "tasks": [],
  "currentPhase": "idle",
  "startedAt": null,
  "updatedAt": null,
  "stats": {
    "totalTasks": 0,
    "completedTasks": 0,
    "failedTasks": 0,
    "runningTasks": 0
  }
}
```

**📄 .paralleldev/config.json 模板**：
```json
{
  "maxWorkers": 3,
  "worktreeDir": ".worktrees",
  "mainBranch": "main",
  "socketPort": 3001,
  "heartbeatInterval": 30000,
  "taskTimeout": 600000,
  "schedulingStrategy": "priority_first"
}
```

**📄 .taskmaster/tasks/tasks.json.example 模板**：
```json
{
  "tasks": [
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
    },
    {
      "id": "3",
      "title": "任务3：实现用户认证",
      "description": "实现 JWT 认证系统（无依赖，可与任务1并行）",
      "status": "pending",
      "priority": 1,
      "dependencies": []
    },
    {
      "id": "4",
      "title": "任务4：集成API和认证",
      "description": "将认证中间件集成到 API 接口（依赖任务2和任务3）",
      "status": "pending",
      "priority": 3,
      "dependencies": ["2", "3"]
    }
  ],
  "meta": {
    "generatedAt": "2025-01-01T00:00:00Z",
    "projectName": "Example Project",
    "version": "1.0.0"
  }
}
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

**📄 paralleldev-plugin/.claude-plugin/plugin.json 完整模板**：
```json
{
  "name": "paralleldev",
  "version": "1.0.0",
  "description": "Claude Code 自动化并行开发系统",
  "author": { "name": "ParallelDev Team" },
  "commands": "./commands/",
  "agents": "./agents/",
  "skills": "./skills/",
  "hooks": "./hooks/hooks.json",
  "mcpServers": "./.mcp.json"
}
```
**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.7: 创建 Plugin 斜杠命令（5个）

**步骤**：
```bash
# 1.7.1 创建 5 个命令文件
# 1.7.2 验证命令格式正确
ls -la paralleldev-plugin/commands/
```

**📄 paralleldev-plugin/commands/start.md**：
```markdown
---
description: 启动 ParallelDev 并行执行系统
arguments:
  - name: tasks
    description: 任务文件路径（默认 .taskmaster/tasks/tasks.json）
    required: false
  - name: workers
    description: Worker 数量（默认 3）
    required: false
---

# /pd:start - 启动并行执行

启动 ParallelDev 系统，开始并行执行任务。

## 执行步骤

1. 加载任务文件 `${tasks:-.taskmaster/tasks/tasks.json}`
2. 验证任务依赖图无循环
3. 启动 ${workers:-3} 个 Worker
4. 开始事件驱动调度循环

## 命令

\`\`\`bash
cd ${projectRoot}
node dist/cli-parallel.js run --tasks "${tasks}" --workers ${workers:-3}
\`\`\`
```

**📄 paralleldev-plugin/commands/status.md**：
```markdown
---
description: 查看 ParallelDev 当前状态
---

# /pd:status - 查看状态

显示当前并行执行系统的状态。

## 输出内容

- Worker 状态（idle/busy/error）
- 任务进度（pending/running/completed/failed）
- 资源使用情况

## 命令

\`\`\`bash
node dist/cli-parallel.js status
\`\`\`
```

**📄 paralleldev-plugin/commands/assign.md**：
```markdown
---
description: 手动分配任务给指定 Worker
arguments:
  - name: taskId
    description: 任务 ID
    required: true
  - name: workerId
    description: Worker ID
    required: true
---

# /pd:assign - 手动分配任务

将指定任务分配给指定 Worker。

## 命令

\`\`\`bash
node dist/cli-parallel.js assign --task "${taskId}" --worker "${workerId}"
\`\`\`
```

**📄 paralleldev-plugin/commands/stop.md**：
```markdown
---
description: 停止 ParallelDev 执行
arguments:
  - name: force
    description: 强制停止（不等待当前任务完成）
    required: false
---

# /pd:stop - 停止执行

停止并行执行系统。

## 命令

\`\`\`bash
node dist/cli-parallel.js stop ${force:+--force}
\`\`\`
```

**📄 paralleldev-plugin/commands/report.md**：
```markdown
---
description: 生成执行报告
arguments:
  - name: format
    description: 输出格式（markdown/json）
    required: false
---

# /pd:report - 生成报告

生成当前执行会话的报告。

## 命令

\`\`\`bash
node dist/cli-parallel.js report --format "${format:-markdown}"
\`\`\`
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.8: 创建 Plugin Agents（4个）

**步骤**：
```bash
# 1.8.1 创建 4 个 Agent 文件
# 1.8.2 验证 Agent 配置正确
ls -la paralleldev-plugin/agents/
```

**📄 paralleldev-plugin/agents/task-orchestrator.md**：
```markdown
---
name: task-orchestrator
description: 任务编排专家 - 分析任务依赖、优化执行顺序、识别并行机会
model: sonnet
tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Task Orchestrator Agent

你是 ParallelDev 的任务编排专家。

## 核心职责

1. **分析任务依赖图**：识别任务之间的依赖关系
2. **识别并行机会**：找出可以同时执行的任务集合
3. **优化执行顺序**：根据优先级和依赖关系排序任务
4. **预估执行时间**：基于历史数据估算任务耗时

## 输入

- 任务列表（tasks.json 格式）
- 当前 Worker 数量
- 执行约束条件

## 输出

返回优化后的执行计划，包括：
- 任务执行顺序
- 并行任务组
- 预估总耗时
- 关键路径分析
```

**📄 paralleldev-plugin/agents/quality-gate.md**：
```markdown
---
name: quality-gate
description: 代码质量门禁 - 执行代码检查、测试、类型验证
model: haiku
tools:
  - Bash
  - Read
  - Grep
---

# Quality Gate Agent

你是 ParallelDev 的代码质量门禁。

## 核心职责

1. **TypeScript 类型检查**：运行 `tsc --noEmit`
2. **ESLint 检查**：运行 `eslint src --ext .ts`
3. **单元测试**：运行 `vitest run`
4. **生成质量报告**：汇总所有检查结果

## 检查流程

\`\`\`bash
# 1. 类型检查
tsc --noEmit

# 2. Lint 检查
eslint src --ext .ts

# 3. 单元测试
vitest run --reporter=json
\`\`\`

## 输出

返回质量检查报告：
- 通过/失败状态
- 错误详情列表
- 修复建议
```

**📄 paralleldev-plugin/agents/conflict-resolver.md**：
```markdown
---
name: conflict-resolver
description: Git 冲突解决专家 - 分层解决 merge 冲突
model: sonnet
tools:
  - Read
  - Edit
  - Bash
  - Grep
---

# Conflict Resolver Agent

你是 ParallelDev 的 Git 冲突解决专家。

## 分层解决策略

### Level 1: 自动解决（无需 AI）
- package-lock.json / yarn.lock
- 格式化差异（空格、换行）
- 非重叠的代码修改

### Level 2: AI 辅助解决
- 同一函数的不同修改
- 导入语句冲突
- 配置文件冲突

### Level 3: 需要人工介入
- 业务逻辑冲突
- 架构级别的冲突
- 无法自动判断的情况

## 输出

- 解决状态（resolved/needs_human）
- 解决级别（1/2/3）
- 冲突文件列表
- 解决方案说明
```

**📄 paralleldev-plugin/agents/worker-monitor.md**：
```markdown
---
name: worker-monitor
description: Worker 监控 - 监控 Worker 状态、检测异常
model: haiku
tools:
  - Bash
  - Read
---

# Worker Monitor Agent

你是 ParallelDev 的 Worker 监控专家。

## 监控内容

1. **Worker 状态**：idle/busy/error/offline
2. **心跳检测**：检查最后心跳时间
3. **Tmux 会话状态**：检查会话是否存活
4. **任务执行进度**：监控当前任务状态

## 检测命令

\`\`\`bash
# 检查 tmux 会话
tmux list-sessions | grep "parallel-dev"

# 检查心跳时间（从 state.json 读取）
cat .paralleldev/state.json | jq '.workers[].lastHeartbeat'
\`\`\`

## 输出

- Worker 状态汇总
- 异常 Worker 列表
- 建议操作（重启/清理等）
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.9: 创建核心 Plugin Skills（3个）

**步骤**：
```bash
# 1.9.1 创建 3 个核心 Skill 目录
mkdir -p paralleldev-plugin/skills/parallel-executor
mkdir -p paralleldev-plugin/skills/conflict-resolution
mkdir -p paralleldev-plugin/skills/quality-assurance

# 1.9.2 创建 SKILL.md 文件
# 1.9.3 验证 Skill 结构
tree paralleldev-plugin/skills/
```

**📄 paralleldev-plugin/skills/parallel-executor/SKILL.md**：
```markdown
---
name: parallel-executor
description: 并行任务执行能力 - 管理 Worker、Worktree、任务调度
triggers:
  - parallel
  - 并行
  - worktree
  - worker
  - 任务执行
---

# Parallel Executor Skill

启用 ParallelDev 并行执行能力。

## 能力范围

### Git Worktree 管理
- 创建独立 worktree: `git worktree add .worktrees/task-{id} -b task/{id}`
- 删除 worktree: `git worktree remove .worktrees/task-{id}`
- 列出 worktree: `git worktree list`

### Tmux 会话管理
- 创建会话: `tmux new-session -d -s parallel-dev-{id}`
- 发送命令: `tmux send-keys -t parallel-dev-{id} 'command' Enter`
- 捕获输出: `tmux capture-pane -t parallel-dev-{id} -p`

### Claude Headless 执行
- 启动命令: `claude -p "task prompt" --output-format stream-json`
- 解析 stream-json 输出
- 检测任务完成状态

## 使用示例

\`\`\`typescript
// 创建 Worker
const worktree = await worktreeManager.create('task-1');
const tmux = await tmuxController.createSession('parallel-dev-1', worktree.path);
await taskExecutor.execute(task, worktree.path);
\`\`\`
```

**📄 paralleldev-plugin/skills/conflict-resolution/SKILL.md**：
```markdown
---
name: conflict-resolution
description: Git 冲突解决能力 - 分层策略自动解决 merge 冲突
triggers:
  - conflict
  - 冲突
  - merge
  - rebase
  - CONFLICT
---

# Conflict Resolution Skill

启用 ParallelDev 冲突解决能力。

## 分层策略

### Level 1: 自动解决
文件类型：
- `package-lock.json` → 重新生成
- `yarn.lock` → 重新生成
- `.prettierrc` 等配置 → 保留 ours

命令：
\`\`\`bash
git checkout --ours package-lock.json
npm install
\`\`\`

### Level 2: AI 辅助
使用 conflict-resolver Agent 分析并解决。

### Level 3: 人工介入
生成冲突报告，通知用户手动处理。
```

**📄 paralleldev-plugin/skills/quality-assurance/SKILL.md**：
```markdown
---
name: quality-assurance
description: 代码质量保证能力 - TypeScript、ESLint、测试验证
triggers:
  - 质量检查
  - quality
  - lint
  - typecheck
  - test
---

# Quality Assurance Skill

启用 ParallelDev 质量保证能力。

## 检查项目

### TypeScript 类型检查
\`\`\`bash
tsc --noEmit --pretty
\`\`\`

### ESLint 代码规范
\`\`\`bash
eslint src --ext .ts --format stylish
\`\`\`

### 单元测试
\`\`\`bash
vitest run --reporter=verbose
\`\`\`

## 质量门禁

所有检查必须通过才能：
1. 合并代码到主分支
2. 标记任务为完成
3. 推送到远程仓库
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.10: 创建语言相关 Skills（4个）

**步骤**：
```bash
# 1.10.1 创建 4 个语言 Skill 目录
mkdir -p paralleldev-plugin/skills/frontend-development
mkdir -p paralleldev-plugin/skills/go-development
mkdir -p paralleldev-plugin/skills/java-development
mkdir -p paralleldev-plugin/skills/typescript-development

# 1.10.2 创建 SKILL.md 文件
```

**📄 paralleldev-plugin/skills/frontend-development/SKILL.md**：
```markdown
---
name: frontend-development
description: 前端开发规范 - React/Vue/Nuxt3 最佳实践
triggers:
  - React
  - Vue
  - Nuxt
  - 前端
  - component
  - 组件
---

# Frontend Development Skill

前端开发规范和最佳实践。

## React 规范
- 函数组件 + Hooks（优先）
- TypeScript 严格模式
- CSS-in-JS 或 Tailwind CSS

## Vue 3 规范
- Composition API
- \`<script setup>\` 语法
- Pinia 状态管理

## Nuxt 3 规范
- 自动导入
- 文件路由
- Nitro 服务器
```

**📄 paralleldev-plugin/skills/go-development/SKILL.md**：
```markdown
---
name: go-development
description: Go 开发规范 - Go 1.23+ 最佳实践
triggers:
  - Go
  - Golang
  - go.mod
---

# Go Development Skill

Go 1.23+ 开发规范。

## 代码规范
- 使用 gofmt 格式化
- golangci-lint 检查
- 表驱动测试

## 项目结构
- cmd/：入口点
- internal/：私有包
- pkg/：公共包
```

**📄 paralleldev-plugin/skills/java-development/SKILL.md**：
```markdown
---
name: java-development
description: Java 开发规范 - JDK 17+ 最佳实践
triggers:
  - Java
  - Spring
  - Maven
  - Gradle
---

# Java Development Skill

JDK 17+ 开发规范。

## 代码规范
- Records 替代 POJO
- Pattern Matching
- Sealed Classes

## 框架
- Spring Boot 3.x
- Quarkus / Micronaut
```

**📄 paralleldev-plugin/skills/typescript-development/SKILL.md**：
```markdown
---
name: typescript-development
description: TypeScript 开发规范 - 严格类型最佳实践
triggers:
  - TypeScript
  - ts
  - Node.js
  - npm
---

# TypeScript Development Skill

TypeScript 严格模式开发规范。

## 类型规范
- 禁止 any
- 严格空检查
- Zod 运行时验证

## 项目结构
- src/：源码
- dist/：编译输出
- tests/：测试
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.11: 创建 Plugin Hooks 和 MCP 配置

**步骤**：
```bash
# 1.11.1 创建 hooks.json
# 1.11.2 创建 .mcp.json
# 1.11.3 验证配置格式
```

**📄 paralleldev-plugin/hooks/hooks.json**：
```json
{
  "hooks": [
    {
      "event": "PostToolUse",
      "matcher": {
        "tool": "Edit"
      },
      "command": "bash scripts/notify-change.sh \"$FILE_PATH\""
    },
    {
      "event": "PostToolUse",
      "matcher": {
        "tool": "Write"
      },
      "command": "bash scripts/notify-change.sh \"$FILE_PATH\""
    },
    {
      "event": "Stop",
      "command": "bash scripts/task-completed.sh"
    }
  ]
}
```

**📄 paralleldev-plugin/.mcp.json**：
```json
{
  "mcpServers": {
    "paralleldev-master": {
      "command": "node",
      "args": ["dist/mcp-server.js"],
      "env": {
        "PARALLELDEV_MODE": "master"
      }
    }
  }
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.12: 创建 Plugin 支持脚本

**步骤**：
```bash
# 1.12.1 创建 5 个脚本文件
# 1.12.2 设置执行权限
chmod +x paralleldev-plugin/scripts/*.sh
```

**📄 paralleldev-plugin/scripts/master-start.sh**：
```bash
#!/bin/bash
# 启动 Master Orchestrator
set -e

PROJECT_ROOT="${1:-.}"
WORKERS="${2:-3}"
TASKS_FILE="${3:-.taskmaster/tasks/tasks.json}"

echo "🚀 启动 ParallelDev Master..."
echo "   项目目录: $PROJECT_ROOT"
echo "   Worker 数量: $WORKERS"
echo "   任务文件: $TASKS_FILE"

cd "$PROJECT_ROOT"
node dist/cli-parallel.js run \
  --tasks "$TASKS_FILE" \
  --workers "$WORKERS"
```

**📄 paralleldev-plugin/scripts/worker-start.sh**：
```bash
#!/bin/bash
# 启动单个 Worker
set -e

WORKER_ID="${1:-worker-1}"
WORKTREE_PATH="${2:-.worktrees/$WORKER_ID}"
MASTER_URL="${3:-http://localhost:3001}"

echo "🔧 启动 Worker: $WORKER_ID"
echo "   Worktree: $WORKTREE_PATH"
echo "   Master: $MASTER_URL"

# 创建 tmux 会话
tmux new-session -d -s "parallel-dev-$WORKER_ID" -c "$WORKTREE_PATH"

# 启动 Worker Agent
tmux send-keys -t "parallel-dev-$WORKER_ID" \
  "PARALLELDEV_WORKER_ID=$WORKER_ID PARALLELDEV_MASTER_URL=$MASTER_URL node dist/worker-agent.js" Enter
```

**📄 paralleldev-plugin/scripts/cleanup.sh**：
```bash
#!/bin/bash
# 清理所有 ParallelDev 资源
set -e

echo "🧹 清理 ParallelDev 资源..."

# 1. 杀死所有 tmux 会话
tmux list-sessions 2>/dev/null | grep "parallel-dev" | cut -d: -f1 | while read session; do
  echo "   关闭 tmux 会话: $session"
  tmux kill-session -t "$session" 2>/dev/null || true
done

# 2. 删除所有 worktree
if [ -d ".worktrees" ]; then
  echo "   删除 worktree 目录..."
  git worktree list | grep ".worktrees" | awk '{print $1}' | while read wt; do
    git worktree remove "$wt" --force 2>/dev/null || true
  done
  rm -rf .worktrees
fi

# 3. 清理状态文件
if [ -f ".paralleldev/state.json" ]; then
  echo "   重置状态文件..."
  echo '{"workers":[],"tasks":[],"currentPhase":"idle"}' > .paralleldev/state.json
fi

echo "✅ 清理完成"
```

**📄 paralleldev-plugin/scripts/notify-change.sh**：
```bash
#!/bin/bash
# 通知 Master 文件变更
FILE_PATH="$1"

if [ -n "$PARALLELDEV_MASTER_URL" ]; then
  curl -s -X POST "$PARALLELDEV_MASTER_URL/api/file-changed" \
    -H "Content-Type: application/json" \
    -d "{\"file\": \"$FILE_PATH\", \"worker\": \"$PARALLELDEV_WORKER_ID\"}" \
    > /dev/null 2>&1 || true
fi
```

**📄 paralleldev-plugin/scripts/task-completed.sh**：
```bash
#!/bin/bash
# 通知 Master 任务完成

if [ -n "$PARALLELDEV_MASTER_URL" ] && [ -n "$PARALLELDEV_TASK_ID" ]; then
  curl -s -X POST "$PARALLELDEV_MASTER_URL/api/task-completed" \
    -H "Content-Type: application/json" \
    -d "{\"taskId\": \"$PARALLELDEV_TASK_ID\", \"worker\": \"$PARALLELDEV_WORKER_ID\", \"status\": \"completed\"}" \
    > /dev/null 2>&1 || true
fi
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 1.13: 配置项目 .claude/ 目录

**步骤**：
```bash
# 1.13.1 确保 .claude 目录存在
mkdir -p .claude

# 1.13.2 创建 settings.json
# 1.13.3 验证配置
cat .claude/settings.json
```

**📄 .claude/settings.json**：
```json
{
  "plugins": ["paralleldev@local"],
  "localPlugins": {
    "paralleldev": "./paralleldev-plugin"
  }
}
```

**完成后**：task agent 自测 → 询问是否提交推送

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

## Phase 2: Layer 1 任务管理（爆改代码）

**目标**：实现任务依赖图和调度器

### TODO 2.1: 爆改/保留 TaskDAG.ts

**文件**: `src/parallel/task/TaskDAG.ts`

**步骤**：
```bash
# 2.1.1 对比 task-master 版本
diff claude-task-master/src/???/dag.ts src/parallel/task/TaskDAG.ts || true

# 2.1.2 选择更优实现或合并
# 2.1.3 编写单元测试
# 2.1.4 运行测试验证
vitest run src/parallel/task/TaskDAG.test.ts
```

**📄 src/parallel/task/TaskDAG.ts 完整接口**：
```typescript
/**
 * 任务依赖有向无环图
 * @module parallel/task/TaskDAG
 */

import { Task, TaskStatus } from '../types';

export class TaskDAG {
  private tasks: Map<string, Task> = new Map();
  private completedTasks: Set<string> = new Set();
  private failedTasks: Set<string> = new Set();

  /**
   * 添加任务到 DAG
   * @param task 任务对象
   * @throws Error 如果任务 ID 已存在
   */
  addTask(task: Task): void {
    if (this.tasks.has(task.id)) {
      throw new Error(`任务 ${task.id} 已存在`);
    }
    this.tasks.set(task.id, { ...task });
  }

  /**
   * 批量添加任务
   * @param tasks 任务数组
   */
  addTasks(tasks: Task[]): void {
    for (const task of tasks) {
      this.addTask(task);
    }
  }

  /**
   * 获取可执行任务（依赖已满足且状态为 pending）
   * @returns 可执行任务数组
   */
  getReadyTasks(): Task[] {
    const ready: Task[] = [];
    for (const task of this.tasks.values()) {
      if (task.status !== 'pending') continue;
      const dependenciesMet = task.dependencies.every(
        depId => this.completedTasks.has(depId)
      );
      if (dependenciesMet) {
        ready.push({ ...task });
      }
    }
    return ready;
  }

  /**
   * 标记任务为完成
   * @param taskId 任务 ID
   */
  markCompleted(taskId: string): void {
    const task = this.tasks.get(taskId);
    if (!task) throw new Error(`任务 ${taskId} 不存在`);
    task.status = 'completed';
    task.completedAt = new Date().toISOString();
    this.completedTasks.add(taskId);
  }

  /**
   * 标记任务为失败
   * @param taskId 任务 ID
   * @param error 错误信息
   */
  markFailed(taskId: string, error: string): void {
    const task = this.tasks.get(taskId);
    if (!task) throw new Error(`任务 ${taskId} 不存在`);
    task.status = 'failed';
    task.error = error;
    this.failedTasks.add(taskId);
  }

  /**
   * 标记任务为进行中
   * @param taskId 任务 ID
   * @param workerId 分配的 Worker ID
   */
  markRunning(taskId: string, workerId: string): void {
    const task = this.tasks.get(taskId);
    if (!task) throw new Error(`任务 ${taskId} 不存在`);
    task.status = 'running';
    task.assignedWorker = workerId;
    task.startedAt = new Date().toISOString();
  }

  /**
   * 检测是否存在循环依赖
   * @returns true 如果存在循环
   */
  hasCycle(): boolean {
    const visited = new Set<string>();
    const recStack = new Set<string>();

    const dfs = (taskId: string): boolean => {
      visited.add(taskId);
      recStack.add(taskId);

      const task = this.tasks.get(taskId);
      if (!task) return false;

      for (const depId of task.dependencies) {
        if (!visited.has(depId)) {
          if (dfs(depId)) return true;
        } else if (recStack.has(depId)) {
          return true;
        }
      }

      recStack.delete(taskId);
      return false;
    };

    for (const taskId of this.tasks.keys()) {
      if (!visited.has(taskId)) {
        if (dfs(taskId)) return true;
      }
    }
    return false;
  }

  /**
   * 拓扑排序
   * @returns 排序后的任务 ID 数组
   * @throws Error 如果存在循环依赖
   */
  topologicalSort(): string[] {
    if (this.hasCycle()) {
      throw new Error('存在循环依赖，无法拓扑排序');
    }

    const result: string[] = [];
    const visited = new Set<string>();

    const visit = (taskId: string) => {
      if (visited.has(taskId)) return;
      visited.add(taskId);

      const task = this.tasks.get(taskId);
      if (!task) return;

      for (const depId of task.dependencies) {
        visit(depId);
      }
      result.push(taskId);
    };

    for (const taskId of this.tasks.keys()) {
      visit(taskId);
    }

    return result;
  }

  /**
   * 获取任务
   * @param taskId 任务 ID
   */
  getTask(taskId: string): Task | undefined {
    const task = this.tasks.get(taskId);
    return task ? { ...task } : undefined;
  }

  /**
   * 获取所有任务
   */
  getAllTasks(): Task[] {
    return Array.from(this.tasks.values()).map(t => ({ ...t }));
  }

  /**
   * 获取统计信息
   */
  getStats(): {
    total: number;
    pending: number;
    running: number;
    completed: number;
    failed: number;
  } {
    let pending = 0, running = 0, completed = 0, failed = 0;
    for (const task of this.tasks.values()) {
      switch (task.status) {
        case 'pending': pending++; break;
        case 'running': running++; break;
        case 'completed': completed++; break;
        case 'failed': failed++; break;
      }
    }
    return { total: this.tasks.size, pending, running, completed, failed };
  }
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 2.2: 爆改 TaskScheduler.ts

**文件**: `src/parallel/task/TaskScheduler.ts`

**步骤**：
```bash
# 2.2.1 移除 LOAD_BALANCED 策略
# 2.2.2 保留 PRIORITY_FIRST + DEPENDENCY_FIRST
# 2.2.3 编写单元测试
vitest run src/parallel/task/TaskScheduler.test.ts
```

**📄 src/parallel/task/TaskScheduler.ts 完整接口**：
```typescript
/**
 * 任务调度器
 * @module parallel/task/TaskScheduler
 */

import { Task, SchedulingStrategy } from '../types';
import { TaskDAG } from './TaskDAG';

export class TaskScheduler {
  private strategy: SchedulingStrategy;
  private dag: TaskDAG;

  constructor(dag: TaskDAG, strategy: SchedulingStrategy = 'priority_first') {
    this.dag = dag;
    this.strategy = strategy;
  }

  /**
   * 设置调度策略
   * @param strategy 调度策略
   */
  setStrategy(strategy: SchedulingStrategy): void {
    this.strategy = strategy;
  }

  /**
   * 获取当前调度策略
   */
  getStrategy(): SchedulingStrategy {
    return this.strategy;
  }

  /**
   * 调度任务（返回排序后的可执行任务列表）
   * @returns 排序后的任务数组
   */
  schedule(): Task[] {
    const readyTasks = this.dag.getReadyTasks();

    switch (this.strategy) {
      case 'priority_first':
        return this.sortByPriority(readyTasks);
      case 'dependency_first':
        return this.sortByDependencyUnlock(readyTasks);
      default:
        return readyTasks;
    }
  }

  /**
   * 按优先级排序（数字越小优先级越高）
   */
  private sortByPriority(tasks: Task[]): Task[] {
    return [...tasks].sort((a, b) => a.priority - b.priority);
  }

  /**
   * 按解锁依赖数量排序（能解锁更多任务的优先）
   */
  private sortByDependencyUnlock(tasks: Task[]): Task[] {
    const allTasks = this.dag.getAllTasks();

    // 计算每个任务被多少其他任务依赖
    const dependentCount = new Map<string, number>();
    for (const task of tasks) {
      let count = 0;
      for (const t of allTasks) {
        if (t.dependencies.includes(task.id) && t.status === 'pending') {
          count++;
        }
      }
      dependentCount.set(task.id, count);
    }

    return [...tasks].sort((a, b) => {
      const countA = dependentCount.get(a.id) || 0;
      const countB = dependentCount.get(b.id) || 0;
      // 能解锁更多任务的优先
      if (countB !== countA) return countB - countA;
      // 相同时按优先级
      return a.priority - b.priority;
    });
  }

  /**
   * 获取下一个要执行的任务
   * @returns 下一个任务，如果没有则返回 undefined
   */
  getNextTask(): Task | undefined {
    const scheduled = this.schedule();
    return scheduled[0];
  }

  /**
   * 获取可并行执行的任务组
   * @param maxWorkers 最大 Worker 数量
   * @returns 可并行执行的任务数组
   */
  getParallelTasks(maxWorkers: number): Task[] {
    const scheduled = this.schedule();
    return scheduled.slice(0, maxWorkers);
  }
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 2.3: 爆改 TaskManager.ts（原 TaskMasterAdapter）

**文件**: `src/parallel/task/TaskManager.ts`

**步骤**：
```bash
# 2.3.1 重命名为 TaskManager
# 2.3.2 使用 Zod 验证
# 2.3.3 编写单元测试
vitest run src/parallel/task/TaskManager.test.ts
```

**📄 src/parallel/task/TaskManager.ts 完整接口**：
```typescript
/**
 * 任务管理器（原 TaskMasterAdapter）
 * @module parallel/task/TaskManager
 */

import * as fs from 'fs';
import * as path from 'path';
import { Task, TasksFileSchema } from '../types';
import { TaskDAG } from './TaskDAG';
import { TaskScheduler } from './TaskScheduler';
import { ParallelDevConfig } from '../config';

export class TaskManager {
  private projectRoot: string;
  private tasksFilePath: string;
  private dag: TaskDAG;
  private scheduler: TaskScheduler;

  constructor(projectRoot: string, config: ParallelDevConfig) {
    this.projectRoot = projectRoot;
    this.tasksFilePath = path.join(
      projectRoot,
      '.taskmaster/tasks/tasks.json'
    );
    this.dag = new TaskDAG();
    this.scheduler = new TaskScheduler(this.dag, config.schedulingStrategy);
  }

  /**
   * 检查任务文件是否存在
   */
  tasksFileExists(): boolean {
    return fs.existsSync(this.tasksFilePath);
  }

  /**
   * 加载任务文件
   * @throws Error 如果文件不存在或格式错误
   */
  async loadTasks(): Promise<Task[]> {
    if (!this.tasksFileExists()) {
      throw new Error(`任务文件不存在: ${this.tasksFilePath}`);
    }

    const content = fs.readFileSync(this.tasksFilePath, 'utf-8');
    const data = JSON.parse(content);

    // Zod 验证
    const result = TasksFileSchema.safeParse(data);
    if (!result.success) {
      throw new Error(`任务文件格式错误: ${result.error.message}`);
    }

    // 添加到 DAG
    this.dag = new TaskDAG();
    this.dag.addTasks(result.data.tasks as Task[]);

    // 检测循环依赖
    if (this.dag.hasCycle()) {
      throw new Error('任务存在循环依赖');
    }

    return this.dag.getAllTasks();
  }

  /**
   * 保存任务状态
   */
  async saveTasks(): Promise<void> {
    const tasks = this.dag.getAllTasks();
    const data = {
      tasks,
      meta: {
        generatedAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
    };
    fs.writeFileSync(this.tasksFilePath, JSON.stringify(data, null, 2));
  }

  /**
   * 验证单个任务
   * @param task 任务对象
   * @returns 验证结果
   */
  validateTask(task: Partial<Task>): {
    valid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    if (!task.id || task.id.trim() === '') {
      errors.push('任务 ID 不能为空');
    }
    if (!task.title || task.title.trim() === '') {
      errors.push('任务标题不能为空');
    }
    if (task.priority !== undefined && (task.priority < 1 || task.priority > 5)) {
      errors.push('优先级必须在 1-5 之间');
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * 获取 DAG 实例
   */
  getDAG(): TaskDAG {
    return this.dag;
  }

  /**
   * 获取调度器实例
   */
  getScheduler(): TaskScheduler {
    return this.scheduler;
  }

  /**
   * 获取可执行任务
   */
  getReadyTasks(): Task[] {
    return this.dag.getReadyTasks();
  }

  /**
   * 调度下一批任务
   * @param maxWorkers 最大 Worker 数量
   */
  scheduleNextBatch(maxWorkers: number): Task[] {
    return this.scheduler.getParallelTasks(maxWorkers);
  }

  /**
   * 标记任务开始
   */
  markTaskStarted(taskId: string, workerId: string): void {
    this.dag.markRunning(taskId, workerId);
  }

  /**
   * 标记任务完成
   */
  markTaskCompleted(taskId: string): void {
    this.dag.markCompleted(taskId);
  }

  /**
   * 标记任务失败
   */
  markTaskFailed(taskId: string, error: string): void {
    this.dag.markFailed(taskId, error);
  }

  /**
   * 检查是否所有任务已完成
   */
  isAllCompleted(): boolean {
    const stats = this.dag.getStats();
    return stats.pending === 0 && stats.running === 0;
  }

  /**
   * 获取统计信息
   */
  getStats() {
    return this.dag.getStats();
  }
}
```

**完成后**：task agent 自测 → 询问是否提交推送

**Phase 2 验收标准**：
- [ ] `TaskDAG.getReadyTasks()` 正确返回可执行任务
- [ ] `TaskDAG.hasCycle()` 正确检测循环依赖
- [ ] `TaskScheduler.schedule()` 按策略排序任务
- [ ] `TaskManager.loadTasks()` 能加载 tasks.json
- [ ] 所有单元测试通过

---

## Phase 3: Layer 3 执行层（Tmux + Worktree）

**目标**：实现 Git Worktree 管理和 Tmux 会话控制

### TODO 3.1: 实现 WorktreeManager.ts

**文件**: `src/parallel/git/WorktreeManager.ts`

**📄 完整接口**：
```typescript
/**
 * Git Worktree 管理器
 * @module parallel/git/WorktreeManager
 */

import { execSync } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export interface WorktreeInfo {
  path: string;
  branch: string;
  taskId: string;
  createdAt: string;
}

export class WorktreeManager {
  private projectRoot: string;
  private worktreeDir: string;

  constructor(projectRoot: string, worktreeDir: string = '.worktrees') {
    this.projectRoot = projectRoot;
    this.worktreeDir = path.join(projectRoot, worktreeDir);
  }

  /**
   * 创建 worktree
   * @param taskId 任务 ID
   * @param baseBranch 基础分支（默认 main）
   */
  async create(taskId: string, baseBranch: string = 'main'): Promise<WorktreeInfo> {
    const worktreePath = path.join(this.worktreeDir, `task-${taskId}`);
    const branchName = `task/${taskId}`;

    // 确保目录存在
    if (!fs.existsSync(this.worktreeDir)) {
      fs.mkdirSync(this.worktreeDir, { recursive: true });
    }

    // 创建 worktree
    execSync(
      `git worktree add "${worktreePath}" -b "${branchName}" "${baseBranch}"`,
      { cwd: this.projectRoot, stdio: 'pipe' }
    );

    return {
      path: worktreePath,
      branch: branchName,
      taskId,
      createdAt: new Date().toISOString()
    };
  }

  /**
   * 删除 worktree
   * @param taskId 任务 ID
   */
  async remove(taskId: string): Promise<void> {
    const worktreePath = path.join(this.worktreeDir, `task-${taskId}`);
    execSync(
      `git worktree remove "${worktreePath}" --force`,
      { cwd: this.projectRoot, stdio: 'pipe' }
    );
  }

  /**
   * 列出所有 worktree
   */
  list(): WorktreeInfo[] {
    const output = execSync('git worktree list --porcelain', {
      cwd: this.projectRoot, encoding: 'utf-8'
    });
    // 解析输出...
    return [];
  }

  /**
   * 检查 worktree 是否存在
   */
  exists(taskId: string): boolean {
    const worktreePath = path.join(this.worktreeDir, `task-${taskId}`);
    return fs.existsSync(worktreePath);
  }

  /**
   * 清理所有 worktree
   */
  async cleanup(): Promise<void> {
    const worktrees = this.list();
    for (const wt of worktrees) {
      if (wt.path.includes(this.worktreeDir)) {
        await this.remove(wt.taskId);
      }
    }
  }
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 3.2: 实现 ConflictDetector.ts

**文件**: `src/parallel/git/ConflictDetector.ts`

**📄 完整接口**：
```typescript
/**
 * Git 冲突检测器
 * @module parallel/git/ConflictDetector
 */

import { execSync } from 'child_process';
import { ConflictLevel, ConflictInfo } from '../types';

export class ConflictDetector {
  /**
   * 检测 worktree 中的冲突
   * @param worktreePath worktree 路径
   */
  async detectConflicts(worktreePath: string): Promise<ConflictInfo[]> {
    const conflicts: ConflictInfo[] = [];

    // 检查 git status
    const status = execSync('git status --porcelain', {
      cwd: worktreePath, encoding: 'utf-8'
    });

    // 解析冲突文件 (UU 标记)
    const lines = status.split('\n');
    for (const line of lines) {
      if (line.startsWith('UU ')) {
        const file = line.substring(3).trim();
        const level = this.getConflictLevel(file);
        conflicts.push({
          file,
          level,
          conflictMarkers: await this.getConflictMarkers(worktreePath, file)
        });
      }
    }

    return conflicts;
  }

  /**
   * 检查是否有冲突
   */
  async hasConflicts(worktreePath: string): Promise<boolean> {
    const conflicts = await this.detectConflicts(worktreePath);
    return conflicts.length > 0;
  }

  /**
   * 获取冲突级别
   */
  getConflictLevel(file: string): ConflictLevel {
    // Level 1: 自动解决
    const autoResolvable = [
      'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
      '.prettierrc', '.eslintrc'
    ];
    if (autoResolvable.some(f => file.endsWith(f))) {
      return 1;
    }

    // Level 2: AI 辅助
    const aiResolvable = ['.ts', '.js', '.json', '.md'];
    if (aiResolvable.some(ext => file.endsWith(ext))) {
      return 2;
    }

    // Level 3: 人工介入
    return 3;
  }

  /**
   * 获取冲突标记内容
   */
  private async getConflictMarkers(
    worktreePath: string, file: string
  ): Promise<string[]> {
    // 读取文件并提取 <<<<<<< / ======= / >>>>>>> 之间的内容
    return [];
  }
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 3.3: 实现 TmuxController.ts

**文件**: `src/parallel/tmux/TmuxController.ts`

**📄 完整接口**：
```typescript
/**
 * Tmux 会话控制器
 * @module parallel/tmux/TmuxController
 */

import { execSync, spawn } from 'child_process';

export class TmuxController {
  private sessionPrefix: string;

  constructor(sessionPrefix: string = 'parallel-dev') {
    this.sessionPrefix = sessionPrefix;
  }

  /**
   * 创建新的 tmux 会话
   * @param sessionId 会话 ID
   * @param workingDir 工作目录
   */
  async createSession(sessionId: string, workingDir: string): Promise<string> {
    const sessionName = `${this.sessionPrefix}-${sessionId}`;
    execSync(
      `tmux new-session -d -s "${sessionName}" -c "${workingDir}"`,
      { stdio: 'pipe' }
    );
    return sessionName;
  }

  /**
   * 杀死 tmux 会话
   */
  async killSession(sessionName: string): Promise<void> {
    execSync(`tmux kill-session -t "${sessionName}"`, { stdio: 'pipe' });
  }

  /**
   * 向会话发送命令
   */
  async sendCommand(sessionName: string, command: string): Promise<void> {
    execSync(
      `tmux send-keys -t "${sessionName}" '${command}' Enter`,
      { stdio: 'pipe' }
    );
  }

  /**
   * 捕获会话输出
   */
  async captureOutput(sessionName: string, lines: number = 1000): Promise<string> {
    return execSync(
      `tmux capture-pane -t "${sessionName}" -p -S -${lines}`,
      { encoding: 'utf-8' }
    );
  }

  /**
   * 列出所有会话
   */
  listSessions(): string[] {
    try {
      const output = execSync('tmux list-sessions -F "#{session_name}"', {
        encoding: 'utf-8'
      });
      return output.trim().split('\n')
        .filter(s => s.startsWith(this.sessionPrefix));
    } catch {
      return [];
    }
  }

  /**
   * 检查会话是否存在
   */
  sessionExists(sessionName: string): boolean {
    return this.listSessions().includes(sessionName);
  }
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 3.4: 实现 SessionMonitor.ts

**文件**: `src/parallel/tmux/SessionMonitor.ts`

**📄 完整接口**：
```typescript
/**
 * Tmux 会话监控器
 * @module parallel/tmux/SessionMonitor
 */

import { TmuxController } from './TmuxController';
import { EventEmitter } from 'events';

export class SessionMonitor extends EventEmitter {
  private tmux: TmuxController;
  private sessions: Map<string, NodeJS.Timeout> = new Map();
  private checkInterval: number;

  constructor(tmux: TmuxController, checkInterval: number = 1000) {
    super();
    this.tmux = tmux;
    this.checkInterval = checkInterval;
  }

  /**
   * 开始监控会话
   */
  startMonitoring(sessionName: string): void {
    if (this.sessions.has(sessionName)) return;

    let lastOutput = '';
    const timer = setInterval(async () => {
      const output = await this.tmux.captureOutput(sessionName);
      if (output !== lastOutput) {
        const newContent = output.slice(lastOutput.length);
        this.emit('output', { sessionName, content: newContent });
        lastOutput = output;
      }
    }, this.checkInterval);

    this.sessions.set(sessionName, timer);
  }

  /**
   * 停止监控会话
   */
  stopMonitoring(sessionName: string): void {
    const timer = this.sessions.get(sessionName);
    if (timer) {
      clearInterval(timer);
      this.sessions.delete(sessionName);
    }
  }

  /**
   * 停止所有监控
   */
  stopAll(): void {
    for (const sessionName of this.sessions.keys()) {
      this.stopMonitoring(sessionName);
    }
  }
}
```

**完成后**：task agent 自测 → 询问是否提交推送

### TODO 3.5: 实现 TaskExecutor.ts

**文件**: `src/parallel/worker/TaskExecutor.ts`

**📄 完整接口**：
```typescript
/**
 * 任务执行器
 * @module parallel/worker/TaskExecutor
 */

import { Task, TaskResult } from '../types';
import { TmuxController } from '../tmux/TmuxController';
import { SessionMonitor } from '../tmux/SessionMonitor';

export class TaskExecutor {
  private tmux: TmuxController;
  private monitor: SessionMonitor;
  private tmuxSession: string;

  constructor(tmux: TmuxController, monitor: SessionMonitor, tmuxSession: string) {
    this.tmux = tmux;
    this.monitor = monitor;
    this.tmuxSession = tmuxSession;
  }

  /**
   * 执行任务
   * @param task 任务对象
   * @param worktreePath worktree 路径
   */
  async execute(task: Task, worktreePath: string): Promise<TaskResult> {
    // 1. 构建任务 Prompt
    const prompt = this.buildTaskPrompt(task);

    // 2. 构建 Claude Headless 命令
    const claudeCommand = [
      'claude',
      '-p', `"${prompt}"`,
      '--output-format', 'stream-json',
      '--permission-mode', 'acceptEdits',
      '--allowedTools', 'Read,Edit,Write,Bash,Grep,Glob'
    ].join(' ');

    // 3. 在 Tmux 中执行
    await this.tmux.sendCommand(this.tmuxSession, claudeCommand);

    // 4. 监控输出并等待完成
    return await this.waitForCompletion();
  }

  /**
   * 构建任务 Prompt
   */
  private buildTaskPrompt(task: Task): string {
    return `
你是 ParallelDev Worker，正在执行任务。

## 任务信息
- ID: ${task.id}
- 标题: ${task.title}
- 描述: ${task.description}

## 执行要求
1. 完成任务描述中的所有需求
2. 遵循项目代码规范
3. 编写必要的测试
4. 任务完成后输出 "TASK_COMPLETED"

开始执行任务。
    `.trim();
  }

  /**
   * 等待任务完成
   */
  private async waitForCompletion(): Promise<TaskResult> {
    return new Promise((resolve) => {
      const checkCompletion = async () => {
        const output = await this.tmux.captureOutput(this.tmuxSession);
        const events = this.parseStreamJson(output);

        for (const event of events) {
          if (event.type === 'result') {
            resolve({ success: true, output: event.result });
            return;
          }
          if (event.type === 'error') {
            resolve({ success: false, error: event.error });
            return;
          }
        }

        // 继续检查
        setTimeout(checkCompletion, 1000);
      };

      checkCompletion();
    });
  }

  /**
   * 解析 stream-json 输出
   */
  private parseStreamJson(output: string): Array<{type: string; [key: string]: any}> {
    const events: Array<{type: string; [key: string]: any}> = [];
    const lines = output.split('\n');

    for (const line of lines) {
      if (line.startsWith('{') && line.endsWith('}')) {
        try {
          events.push(JSON.parse(line));
        } catch {}
      }
    }

    return events;
  }
}
```

**完成后**：task agent 自测 → 询问是否提交推送

**Phase 3 验收标准**：
- [ ] Worktree 创建/删除正常
- [ ] Tmux 会话控制正常
- [ ] Claude Headless 可在 Tmux 中执行

---

## Phase 4: Layer 4 通信层（Socket.IO + RPC）

**目标**：实现 Master-Worker 双向通信

### TODO 4.1: 爆改 SocketClient.ts

**文件**: `src/parallel/communication/SocketClient.ts`

**核心接口**：
```typescript
export class SocketClient {
  connect(url: string): Promise<void>;
  disconnect(): void;
  emit(event: string, data: any): void;
  on(event: string, handler: (data: any) => void): void;
  off(event: string, handler?: (data: any) => void): void;
  isConnected(): boolean;
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

**核心接口**：
```typescript
export class RpcManager {
  registerHandler(method: string, handler: (params: any) => Promise<any>): void;
  call(method: string, params: any): Promise<any>;
  unregisterHandler(method: string): void;
}
```

**完成后**：task agent 自测 → 询问是否提交推送

**Phase 4 验收标准**：
- [ ] Socket.IO 连接正常
- [ ] Worker 可向 Master 报告状态
- [ ] Master 可向 Worker 分配任务

---

## Phase 5: Layer 5 质量保证层

**目标**：实现代码质量检查和冲突解决

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

export interface CheckResult {
  passed: boolean;
  errors: string[];
  warnings: string[];
}

export interface TestResult {
  passed: boolean;
  total: number;
  failed: number;
  failures: string[];
}
```

**完成后**：task agent 自测 → 询问是否提交推送

**Phase 5 验收标准**：
- [ ] Subagent 可正常调用
- [ ] 冲突解决流程正常（Level 1/2/3）
- [ ] 代码验证流程正常（TypeScript + ESLint + Tests）

---

## Phase 6: Layer 2 编排层

**目标**：实现主控制器和状态管理

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
   * 添加 Worker
   */
  addWorker(worker: Worker): void;

  /**
   * 移除 Worker
   */
  removeWorker(workerId: string): void;

  /**
   * 获取空闲 Worker
   */
  getIdleWorker(): Worker | undefined;

  /**
   * 设置 Worker 状态
   */
  setWorkerStatus(workerId: string, status: WorkerStatus): void;

  /**
   * 获取 Worker 状态
   */
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
}
```

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
   * 保存状态到文件
   */
  async saveState(state: SystemState): Promise<void>;

  /**
   * 从文件加载状态
   */
  async loadState(): Promise<SystemState | null>;

  /**
   * 获取当前状态
   */
  getState(): SystemState;

  /**
   * 更新状态
   */
  updateState(partial: Partial<SystemState>): void;

  /**
   * 重置状态
   */
  resetState(): void;

  /**
   * 自动保存（定时）
   */
  startAutoSave(intervalMs?: number): void;

  /**
   * 停止自动保存
   */
  stopAutoSave(): void;
}
```

**完成后**：task agent 自测 → 询问是否提交推送

**Phase 6 验收标准**：
- [ ] Master 编排流程正常（事件驱动）
- [ ] Worker 池管理正常
- [ ] 状态持久化正常

---

## Phase 7: Layer 6 通知层

**目标**：实现通知和报告生成

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
   * 通知任务完成
   */
  async notifyTaskCompleted(task: Task): Promise<void>;

  /**
   * 通知任务失败
   */
  async notifyTaskFailed(task: Task, error: string): Promise<void>;

  /**
   * 通知所有任务完成
   */
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
   * 格式化为 Markdown
   */
  formatMarkdown(report: ExecutionReport): string;

  /**
   * 格式化为 JSON
   */
  formatJson(report: ExecutionReport): string;

  /**
   * 保存报告到文件
   */
  async saveReport(report: ExecutionReport, format: 'markdown' | 'json'): Promise<string>;
}
```

**完成后**：task agent 自测 → 询问是否提交推送

**Phase 7 验收标准**：
- [ ] 通知功能正常（终端/声音）
- [ ] 报告生成正常（Markdown/JSON）

---

## Phase 8: 集成测试 + CLI

**目标**：完整端到端测试

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

**📄 src/cli-parallel.ts 完整模板**：
```typescript
#!/usr/bin/env node
/**
 * ParallelDev CLI 入口
 * @module cli-parallel
 */

import { Command } from 'commander';
import { MasterOrchestrator } from './parallel/master/MasterOrchestrator';
import { StateManager } from './parallel/master/StateManager';
import { ReportGenerator } from './parallel/notification/ReportGenerator';
import { loadConfig, validateConfig } from './parallel/config';
import { SchedulingStrategy } from './parallel/types';

const program = new Command();

program
  .name('paralleldev')
  .description('Claude Code 自动化并行开发系统')
  .version('1.0.0');

/**
 * run 命令：启动并行执行
 */
program
  .command('run')
  .description('启动并行执行系统')
  .option('-t, --tasks <path>', '任务文件路径', '.taskmaster/tasks/tasks.json')
  .option('-w, --workers <number>', 'Worker 数量', '3')
  .option('-s, --strategy <strategy>', '调度策略 (priority_first|dependency_first)', 'priority_first')
  .option('-p, --project <path>', '项目根目录', process.cwd())
  .action(async (options) => {
    try {
      console.log('🚀 启动 ParallelDev...');
      console.log(`   任务文件: ${options.tasks}`);
      console.log(`   Worker 数量: ${options.workers}`);
      console.log(`   调度策略: ${options.strategy}`);

      // 1. 加载配置
      const config = loadConfig(options.project);
      config.maxWorkers = parseInt(options.workers, 10);
      config.schedulingStrategy = options.strategy as SchedulingStrategy;

      // 2. 验证配置
      const validation = validateConfig(config);
      if (!validation.valid) {
        console.error('❌ 配置无效:', validation.errors.join(', '));
        process.exit(1);
      }

      // 3. 创建并启动 Master
      const master = new MasterOrchestrator(config, options.project);

      // 4. 处理退出信号
      process.on('SIGINT', async () => {
        console.log('\n⚠️  收到中断信号，正在停止...');
        await master.stop();
        process.exit(0);
      });

      // 5. 启动
      await master.start();

    } catch (error) {
      console.error('❌ 启动失败:', error);
      process.exit(1);
    }
  });

/**
 * status 命令：查看当前状态
 */
program
  .command('status')
  .description('查看当前并行执行状态')
  .option('-p, --project <path>', '项目根目录', process.cwd())
  .option('-f, --format <format>', '输出格式 (text|json)', 'text')
  .action(async (options) => {
    try {
      const stateManager = new StateManager(options.project);
      const state = await stateManager.loadState();

      if (!state) {
        console.log('ℹ️  没有正在运行的会话');
        return;
      }

      if (options.format === 'json') {
        console.log(JSON.stringify(state, null, 2));
      } else {
        console.log('📊 ParallelDev 状态');
        console.log('─'.repeat(40));
        console.log(`状态: ${state.currentPhase}`);
        console.log(`启动时间: ${state.startedAt || 'N/A'}`);
        console.log(`更新时间: ${state.updatedAt || 'N/A'}`);
        console.log('');
        console.log('📦 任务统计:');
        console.log(`   总计: ${state.stats.totalTasks}`);
        console.log(`   已完成: ${state.stats.completedTasks}`);
        console.log(`   进行中: ${state.stats.runningTasks}`);
        console.log(`   失败: ${state.stats.failedTasks}`);
        console.log('');
        console.log('🔧 Worker 统计:');
        console.log(`   活动: ${state.stats.activeWorkers}`);
        console.log(`   空闲: ${state.stats.idleWorkers}`);
      }

    } catch (error) {
      console.error('❌ 获取状态失败:', error);
      process.exit(1);
    }
  });

/**
 * stop 命令：停止执行
 */
program
  .command('stop')
  .description('停止并行执行系统')
  .option('-p, --project <path>', '项目根目录', process.cwd())
  .option('-f, --force', '强制停止（不等待当前任务）', false)
  .action(async (options) => {
    try {
      console.log('⏹️  停止 ParallelDev...');

      const stateManager = new StateManager(options.project);
      const state = await stateManager.loadState();

      if (!state || state.currentPhase === 'idle') {
        console.log('ℹ️  没有正在运行的会话');
        return;
      }

      // 更新状态为停止
      stateManager.updateState({ currentPhase: 'idle' });
      await stateManager.saveState(stateManager.getState());

      if (options.force) {
        console.log('⚠️  强制停止，正在清理资源...');
        // 运行清理脚本
        const { execSync } = require('child_process');
        execSync('bash paralleldev-plugin/scripts/cleanup.sh', {
          cwd: options.project,
          stdio: 'inherit'
        });
      }

      console.log('✅ 已停止');

    } catch (error) {
      console.error('❌ 停止失败:', error);
      process.exit(1);
    }
  });

/**
 * report 命令：生成报告
 */
program
  .command('report')
  .description('生成执行报告')
  .option('-p, --project <path>', '项目根目录', process.cwd())
  .option('-f, --format <format>', '输出格式 (markdown|json)', 'markdown')
  .option('-o, --output <path>', '输出文件路径')
  .action(async (options) => {
    try {
      const stateManager = new StateManager(options.project);
      const state = await stateManager.loadState();

      if (!state) {
        console.log('ℹ️  没有可用的执行数据');
        return;
      }

      const reportGenerator = new ReportGenerator();
      const report = reportGenerator.generateReport(state);

      let output: string;
      if (options.format === 'json') {
        output = reportGenerator.formatJson(report);
      } else {
        output = reportGenerator.formatMarkdown(report);
      }

      if (options.output) {
        const fs = require('fs');
        fs.writeFileSync(options.output, output);
        console.log(`✅ 报告已保存到: ${options.output}`);
      } else {
        console.log(output);
      }

    } catch (error) {
      console.error('❌ 生成报告失败:', error);
      process.exit(1);
    }
  });

// 解析命令行参数
program.parse();
```

**完成后**：task agent 自测（node dist/cli-parallel.js --help）→ 询问是否提交推送

### TODO 8.2: 端到端测试

**测试仓库**: `https://github.com/hexonal/test-demo`

**文件**: `src/parallel/__tests__/e2e.test.ts`

**步骤**：
```bash
# 8.2.1 克隆测试仓库
git clone https://github.com/hexonal/test-demo.git ./test-demo-e2e

# 8.2.2 初始化测试仓库（如果是空的）
cd ./test-demo-e2e
echo "# Test Demo Project" > README.md
echo "用于 ParallelDev E2E 测试的示例项目" >> README.md
git add README.md && git commit -m "init: 初始化测试项目"

# 8.2.3 创建任务文件目录结构
mkdir -p .taskmaster/tasks

# 8.2.4 创建示例任务文件
# 见下方 tasks.json 模板

# 8.2.5 创建测试目录
mkdir -p src/parallel/__tests__

# 8.2.6 创建测试文件
# 8.2.7 运行测试
vitest run src/parallel/__tests__/e2e.test.ts
```

**📄 test-demo-e2e/.taskmaster/tasks/tasks.json 模板**：
```json
{
  "tasks": [
    {
      "id": "1",
      "title": "创建项目基础结构",
      "description": "创建 src/ 目录和基础配置文件",
      "status": "pending",
      "priority": 1,
      "dependencies": []
    },
    {
      "id": "2",
      "title": "实现核心功能模块",
      "description": "在 src/core/ 中实现核心业务逻辑",
      "status": "pending",
      "priority": 2,
      "dependencies": ["1"]
    },
    {
      "id": "3",
      "title": "实现工具函数",
      "description": "在 src/utils/ 中实现通用工具函数（可与任务2并行）",
      "status": "pending",
      "priority": 2,
      "dependencies": ["1"]
    },
    {
      "id": "4",
      "title": "集成测试",
      "description": "编写集成测试验证核心功能和工具函数",
      "status": "pending",
      "priority": 3,
      "dependencies": ["2", "3"]
    }
  ],
  "meta": {
    "generatedAt": "2025-12-08T00:00:00Z",
    "projectName": "test-demo",
    "version": "1.0.0"
  }
}
```

**📄 src/parallel/__tests__/e2e.test.ts 完整模板**：
```typescript
/**
 * ParallelDev 端到端测试
 * @module parallel/__tests__/e2e
 *
 * 使用 https://github.com/hexonal/test-demo 作为测试目标仓库
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

// 测试仓库配置
const TEST_REPO_URL = 'https://github.com/hexonal/test-demo.git';
const TEST_DIR = path.join(__dirname, '../../../test-demo-e2e');
const TASKS_FILE = path.join(TEST_DIR, '.taskmaster/tasks/tasks.json');

describe('ParallelDev E2E Tests', () => {
  beforeAll(() => {
    // 1. 清理旧的测试目录
    if (fs.existsSync(TEST_DIR)) {
      fs.rmSync(TEST_DIR, { recursive: true });
    }

    // 2. 克隆测试仓库
    try {
      execSync(`git clone ${TEST_REPO_URL} ${TEST_DIR}`, { stdio: 'pipe' });
    } catch {
      // 如果克隆失败（网络问题等），创建本地测试仓库
      fs.mkdirSync(TEST_DIR, { recursive: true });
      execSync('git init', { cwd: TEST_DIR });
      execSync('git config user.email "test@test.com"', { cwd: TEST_DIR });
      execSync('git config user.name "Test"', { cwd: TEST_DIR });
      fs.writeFileSync(path.join(TEST_DIR, 'README.md'), '# Test Demo Project');
      execSync('git add . && git commit -m "init"', { cwd: TEST_DIR });
    }

    // 3. 确保有初始提交（如果仓库是空的）
    try {
      execSync('git rev-parse HEAD', { cwd: TEST_DIR, stdio: 'pipe' });
    } catch {
      fs.writeFileSync(path.join(TEST_DIR, 'README.md'), '# Test Demo Project');
      execSync('git add . && git commit -m "init"', { cwd: TEST_DIR });
    }

    // 4. 创建任务文件
    fs.mkdirSync(path.join(TEST_DIR, '.taskmaster/tasks'), { recursive: true });
    fs.writeFileSync(TASKS_FILE, JSON.stringify({
      tasks: [
        {
          id: '1',
          title: '测试任务1',
          description: '创建测试文件',
          status: 'pending',
          priority: 1,
          dependencies: []
        },
        {
          id: '2',
          title: '测试任务2',
          description: '依赖任务1的任务',
          status: 'pending',
          priority: 2,
          dependencies: ['1']
        },
        {
          id: '3',
          title: '测试任务3',
          description: '可并行任务（与任务2同时执行）',
          status: 'pending',
          priority: 2,
          dependencies: ['1']
        },
        {
          id: '4',
          title: '测试任务4',
          description: '最终任务（依赖2和3）',
          status: 'pending',
          priority: 3,
          dependencies: ['2', '3']
        }
      ],
      meta: {
        generatedAt: new Date().toISOString(),
        projectName: 'test-demo',
        version: '1.0.0'
      }
    }, null, 2));
  });

  afterAll(() => {
    // 清理测试工作空间
    if (fs.existsSync(TEST_DIR)) {
      fs.rmSync(TEST_DIR, { recursive: true });
    }
  });

  describe('TaskManager', () => {
    it('应该正确加载任务文件', async () => {
      const { TaskManager } = await import('../task/TaskManager');
      const { loadConfig } = await import('../config');

      const config = loadConfig(TEST_DIR);
      const manager = new TaskManager(TEST_DIR, config);

      expect(manager.tasksFileExists()).toBe(true);

      const tasks = await manager.loadTasks();
      expect(tasks).toHaveLength(2);
      expect(tasks[0].id).toBe('1');
    });

    it('应该正确识别可执行任务', async () => {
      const { TaskManager } = await import('../task/TaskManager');
      const { loadConfig } = await import('../config');

      const config = loadConfig(TEST_DIR);
      const manager = new TaskManager(TEST_DIR, config);
      await manager.loadTasks();

      const readyTasks = manager.getReadyTasks();
      expect(readyTasks).toHaveLength(1);
      expect(readyTasks[0].id).toBe('1');
    });
  });

  describe('TaskDAG', () => {
    it('应该正确检测循环依赖', async () => {
      const { TaskDAG } = await import('../task/TaskDAG');

      const dag = new TaskDAG();
      dag.addTask({
        id: 'a',
        title: 'A',
        description: '',
        status: 'pending',
        priority: 1,
        dependencies: ['b'],
        createdAt: new Date().toISOString()
      });
      dag.addTask({
        id: 'b',
        title: 'B',
        description: '',
        status: 'pending',
        priority: 1,
        dependencies: ['a'],
        createdAt: new Date().toISOString()
      });

      expect(dag.hasCycle()).toBe(true);
    });

    it('应该正确执行拓扑排序', async () => {
      const { TaskDAG } = await import('../task/TaskDAG');

      const dag = new TaskDAG();
      dag.addTask({
        id: '1',
        title: '1',
        description: '',
        status: 'pending',
        priority: 1,
        dependencies: [],
        createdAt: new Date().toISOString()
      });
      dag.addTask({
        id: '2',
        title: '2',
        description: '',
        status: 'pending',
        priority: 1,
        dependencies: ['1'],
        createdAt: new Date().toISOString()
      });

      const sorted = dag.topologicalSort();
      expect(sorted.indexOf('1')).toBeLessThan(sorted.indexOf('2'));
    });
  });

  describe('TaskScheduler', () => {
    it('应该按优先级排序任务', async () => {
      const { TaskDAG } = await import('../task/TaskDAG');
      const { TaskScheduler } = await import('../task/TaskScheduler');

      const dag = new TaskDAG();
      dag.addTask({
        id: 'low',
        title: 'Low',
        description: '',
        status: 'pending',
        priority: 5,
        dependencies: [],
        createdAt: new Date().toISOString()
      });
      dag.addTask({
        id: 'high',
        title: 'High',
        description: '',
        status: 'pending',
        priority: 1,
        dependencies: [],
        createdAt: new Date().toISOString()
      });

      const scheduler = new TaskScheduler(dag, 'priority_first');
      const scheduled = scheduler.schedule();

      expect(scheduled[0].id).toBe('high');
      expect(scheduled[1].id).toBe('low');
    });
  });

  describe('WorktreeManager', () => {
    it('应该正确创建和删除 worktree', async () => {
      const { WorktreeManager } = await import('../git/WorktreeManager');

      const manager = new WorktreeManager(TEST_DIR, '.worktrees');

      // 创建
      const info = await manager.create('test-1');
      expect(info.taskId).toBe('test-1');
      expect(fs.existsSync(info.path)).toBe(true);

      // 检查存在
      expect(manager.exists('test-1')).toBe(true);

      // 删除
      await manager.remove('test-1');
      expect(manager.exists('test-1')).toBe(false);
    });
  });

  describe('Config', () => {
    it('应该正确验证配置', async () => {
      const { validateConfig, DEFAULT_CONFIG } = await import('../config');

      // 有效配置
      const valid = validateConfig(DEFAULT_CONFIG);
      expect(valid.valid).toBe(true);

      // 无效配置
      const invalid = validateConfig({
        ...DEFAULT_CONFIG,
        maxWorkers: 100
      });
      expect(invalid.valid).toBe(false);
    });
  });
});
```

**完成后**：task agent 自测（vitest run）→ 询问是否提交推送

### TODO 8.3: 文档更新

**步骤**：
```bash
# 8.3.1 更新 README.md 快速开始部分
# 8.3.2 更新 CLAUDE.md 开发指南部分
# 8.3.3 验证文档链接有效
```

**README.md 更新内容**（追加到快速开始部分）：
```markdown
### CLI 命令参考

\`\`\`bash
# 启动并行执行
paralleldev run --tasks .taskmaster/tasks/tasks.json --workers 3 --strategy priority_first

# 查看当前状态
paralleldev status

# 停止执行
paralleldev stop

# 强制停止（不等待当前任务）
paralleldev stop --force

# 生成 Markdown 报告
paralleldev report --format markdown --output report.md

# 生成 JSON 报告
paralleldev report --format json
\`\`\`
```

**CLAUDE.md 更新内容**（追加到开发检查清单部分）：
```markdown
### CLI 测试
- [ ] `paralleldev --help` 显示帮助信息
- [ ] `paralleldev run` 正常启动
- [ ] `paralleldev status` 正确显示状态
- [ ] `paralleldev stop` 正常停止
- [ ] `paralleldev report` 生成报告
```

**完成后**：task agent 自测 → 询问是否提交推送

**Phase 8 验收标准**：
- [ ] CLI 命令正常工作（run/status/stop/report）
- [ ] 端到端测试全部通过
- [ ] 文档更新完成

---

## 🏗️ 架构图（严格遵循 README.md）

```
┌──────────────────────────────────────────────────────────────┐
│                     用户（人工值守）                          │
│              使用 claude-task-master 生成任务                │
└─────────────────────┬───────────────────────────────────────┘
                      │ tasks.json
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Layer 1: Task Management                  │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐  │
│  │ TaskManager  │→ │ TaskDAG       │→ │ TaskScheduler   │  │
│  │ (加载任务)   │  │ (依赖图)      │  │ (调度策略)      │  │
│  └──────────────┘  └───────────────┘  └─────────────────┘  │
│  核心实现：                                                  │
│  • TaskManager.loadTasks() → 读取 .taskmaster/tasks/tasks.json │
│  • TaskDAG.getReadyTasks() → 返回无依赖或依赖已完成的任务    │
│  • TaskScheduler.schedule() → PRIORITY_FIRST / DEPENDENCY_FIRST │
└─────────────────────┬───────────────────────────────────────┘
                      │ 任务队列 (Task[])
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 Layer 2: Orchestration (Master)             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         MasterOrchestrator (主控制器)                 │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐ │  │
│  │  │WorkerPool  │  │StateManager│  │SocketServer   │ │  │
│  │  │(Worker池)  │  │(状态持久化)│  │(通信服务)     │ │  │
│  │  └────────────┘  └────────────┘  └────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│  核心实现：                                                  │
│  • MasterOrchestrator.start() → 启动调度循环                │
│  • WorkerPool.getIdleWorker() → 获取空闲 Worker             │
│  • SocketServer.emit('master:task_assign') → 分配任务       │
└─────────────────────┬───────────────────────────────────────┘
                      │ Socket.IO (WebSocket)
                      │ emit('master:task_assign', { task })
        ┌─────────────┼─────────────┬─────────────┐
        ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│            Layer 3: Execution (Worker × N)                  │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Worker 1   │   Worker 2   │   Worker 3   │      ...       │
│ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │                │
│ │Worktree  │ │ │Worktree  │ │ │Worktree  │ │ WorktreeManager│
│ │.worktrees│ │ │.worktrees│ │ │.worktrees│ │ .create(taskId)│
│ │/task-1   │ │ │/task-2   │ │ │/task-3   │ │                │
│ └──────────┘ │ └──────────┘ │ └──────────┘ │                │
│ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │                │
│ │  Tmux    │ │ │  Tmux    │ │ │  Tmux    │ │ TmuxController │
│ │ Session  │ │ │ Session  │ │ │ Session  │ │ .createSession │
│ └──────────┘ │ └──────────┘ │ └──────────┘ │                │
│ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │                │
│ │ Claude   │ │ │ Claude   │ │ │ Claude   │ │ TaskExecutor   │
│ │ Headless │ │ │ Headless │ │ │ Headless │ │ .execute(task) │
│ └──────────┘ │ └──────────┘ │ └──────────┘ │                │
│ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │                │
│ │ Status   │ │ │ Status   │ │ │ Status   │ │ StatusReporter │
│ │ Reporter │ │ │ Reporter │ │ │ Reporter │ │ .reportComplete│
│ └──────────┘ │ └──────────┘ │ └──────────┘ │                │
└──────────────┴──────────────┴──────────────┴────────────────┘
│  核心实现：                                                  │
│  • WorktreeManager.create(taskId) → git worktree add        │
│  • TmuxController.createSession(name, cwd) → tmux new       │
│  • TaskExecutor.execute(task) → claude -p --output-format   │
│  • StatusReporter.reportTaskCompleted() → socket.emit()     │
        │             │             │
        └─────────────┴─────────────┘
                      │ socket.emit('worker:task_completed')
                      ▼
┌─────────────────────────────────────────────────────────────┐
│       Layer 4: Communication (Socket.IO + RPC)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Worker → Master 事件                                 │   │
│  │  • worker:register    → Worker 注册                  │   │
│  │  • worker:heartbeat   → 心跳 (30秒)                  │   │
│  │  • worker:task_started → 任务开始                    │   │
│  │  • worker:task_completed → 任务完成 ✅               │   │
│  │  • worker:task_failed → 任务失败                     │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Master → Worker 命令                                 │   │
│  │  • master:task_assign → 分配任务                     │   │
│  │  • master:task_cancel → 取消任务                     │   │
│  └─────────────────────────────────────────────────────┘   │
│  核心实现：                                                  │
│  • SocketServer 监听 Worker 事件，触发调度                   │
│  • StatusReporter 主动上报状态（非轮询）                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│       Layer 5: Quality Assurance & Git Integration          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Conflict   │  │ Test Runner  │  │  Code Validator  │   │
│  │  Resolver   │  │ (Subagent)   │  │  (Lint/TypeCheck)│   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│  核心实现：                                                  │
│  • ConflictResolver.resolve() → 分层策略 (Level 1/2/3)      │
│  • CodeValidator.validate() → tsc + eslint + vitest         │
│  • SubagentRunner.run('quality-gate') → 调用 Subagent       │
└─────────────────────┬───────────────────────────────────────┘
                      │ git push
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Layer 6: Notification                     │
│  ┌─────────────────┐  ┌──────────────────────────────┐     │
│  │ Notification    │  │ ReportGenerator              │     │
│  │ Manager         │  │ (Markdown 报告)              │     │
│  └─────────────────┘  └──────────────────────────────┘     │
│  核心实现：                                                  │
│  • NotificationManager.notify() → 终端/声音/Webhook         │
│  • ReportGenerator.generate() → 生成执行报告                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 架构可实现性保证 - 核心代码模式

### 1. Layer 1 核心：TaskDAG.getReadyTasks()

```typescript
// src/parallel/task/TaskDAG.ts
export class TaskDAG {
  private tasks: Map<string, Task> = new Map();
  private completedTasks: Set<string> = new Set();

  /**
   * 获取可执行任务（依赖已满足）
   * 这是整个调度系统的核心
   */
  getReadyTasks(): Task[] {
    const ready: Task[] = [];

    for (const task of this.tasks.values()) {
      // 跳过已完成/进行中/失败的任务
      if (task.status !== 'pending') continue;

      // 检查所有依赖是否已完成
      const dependenciesMet = task.dependencies.every(
        depId => this.completedTasks.has(depId)
      );

      if (dependenciesMet) {
        ready.push(task);
      }
    }

    return ready;
  }
}
```

### 2. Layer 2 核心：MasterOrchestrator 调度循环

```typescript
// src/parallel/master/MasterOrchestrator.ts
export class MasterOrchestrator {
  /**
   * 事件驱动的调度循环（非轮询）
   */
  async start(): Promise<void> {
    // 1. 初始化
    await this.taskManager.loadTasks();
    await this.workerPool.initialize(this.config.maxWorkers);

    // 2. 启动 Socket 服务器
    this.socketServer.start(this.config.socketPort);

    // 3. 监听 Worker 事件（事件驱动）
    this.socketServer.on('worker:register', (worker) => {
      this.workerPool.addWorker(worker);
      this.tryAssignTasks(); // 触发调度
    });

    this.socketServer.on('worker:task_completed', async (event) => {
      await this.handleTaskCompleted(event);
      this.tryAssignTasks(); // 触发调度
    });

    // 4. 初始调度
    this.tryAssignTasks();
  }

  /**
   * 尝试分配任务（核心调度逻辑）
   */
  private async tryAssignTasks(): Promise<void> {
    // 获取可执行任务
    const readyTasks = this.taskDAG.getReadyTasks();

    // 按策略排序
    const sortedTasks = this.scheduler.schedule(readyTasks);

    // 分配给空闲 Worker
    for (const task of sortedTasks) {
      const worker = this.workerPool.getIdleWorker();
      if (!worker) break;

      await this.assignTask(worker, task);
    }
  }
}
```

### 3. Layer 3 核心：TaskExecutor 执行 Claude Headless

```typescript
// src/parallel/worker/TaskExecutor.ts
export class TaskExecutor {
  /**
   * 在 Tmux 中执行 Claude Headless
   */
  async execute(task: Task, worktreePath: string): Promise<TaskResult> {
    // 1. 构建任务 Prompt
    const prompt = this.buildTaskPrompt(task);

    // 2. 构建 Claude 命令
    const claudeCommand = [
      'claude',
      '-p', `"${prompt}"`,
      '--output-format', 'stream-json',
      '--permission-mode', 'acceptEdits',
      '--allowedTools', 'Read,Edit,Write,Bash,Grep,Glob'
    ].join(' ');

    // 3. 在 Tmux 中执行
    await this.tmuxController.sendCommand(
      this.tmuxSession,
      claudeCommand
    );

    // 4. 监控输出并解析结果
    return await this.waitForCompletion();
  }

  /**
   * 监控 Tmux 输出，检测任务完成
   */
  private async waitForCompletion(): Promise<TaskResult> {
    while (true) {
      const output = await this.tmuxController.captureOutput(this.tmuxSession);
      const events = this.parseStreamJson(output);

      for (const event of events) {
        if (event.type === 'result') {
          return { success: true, output: event.result };
        }
        if (event.type === 'error') {
          return { success: false, error: event.error };
        }
      }

      await this.sleep(1000); // 1秒检查一次
    }
  }
}
```

### 4. Layer 4 核心：StatusReporter 状态上报

```typescript
// src/parallel/worker/StatusReporter.ts
export class StatusReporter {
  /**
   * 报告任务完成（通过 Socket.IO emit）
   */
  reportTaskCompleted(taskId: string, result: TaskResult): void {
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

### 5. Layer 5 核心：ConflictResolver 分层解决

```typescript
// src/parallel/quality/ConflictResolver.ts
export class ConflictResolver {
  /**
   * 分层冲突解决策略
   */
  async resolve(worktreePath: string): Promise<ResolveResult> {
    const conflicts = await this.detectConflicts(worktreePath);
    if (conflicts.length === 0) return { resolved: true };

    // Level 1: 自动解决（无需 AI）
    const level1Resolved = await this.resolveLevel1(conflicts);
    if (level1Resolved) return { resolved: true, level: 1 };

    // Level 2: AI 辅助解决
    const level2Resolved = await this.resolveLevel2(conflicts);
    if (level2Resolved) return { resolved: true, level: 2 };

    // Level 3: 需要人工介入
    return {
      resolved: false,
      level: 3,
      conflicts: conflicts.map(c => c.file)
    };
  }

  /**
   * Level 1: 自动解决简单冲突
   */
  private async resolveLevel1(conflicts: Conflict[]): Promise<boolean> {
    // 自动解决：package-lock.json, yarn.lock, 格式化差异
    const autoResolvable = ['package-lock.json', 'yarn.lock'];
    // ...
  }
}
```

---

## 🔄 事件驱动流程图

```
┌──────────────────────────────────────────────────────────────┐
│                    事件驱动执行流程                           │
└──────────────────────────────────────────────────────────────┘

1. 启动阶段
   Master.start()
       │
       ├─→ TaskManager.loadTasks()  ─→ 加载 tasks.json
       ├─→ TaskDAG.build()          ─→ 构建依赖图
       ├─→ WorkerPool.initialize()  ─→ 创建 N 个 Worker
       │       │
       │       └─→ 每个 Worker:
       │           ├─→ WorktreeManager.create(taskId)
       │           ├─→ TmuxController.createSession()
       │           └─→ StatusReporter.connect() ─→ emit('worker:register')
       │
       └─→ SocketServer.start()     ─→ 监听 Worker 事件

2. 调度阶段（事件驱动）
   on('worker:register')
       │
       └─→ tryAssignTasks()
           ├─→ TaskDAG.getReadyTasks()
           ├─→ TaskScheduler.schedule()
           └─→ assignTask(worker, task)
               └─→ emit('master:task_assign', { task })

3. 执行阶段
   Worker 收到 'master:task_assign'
       │
       └─→ TaskExecutor.execute(task)
           ├─→ emit('worker:task_started')
           ├─→ TmuxController.sendCommand('claude -p ...')
           ├─→ 监控 stream-json 输出
           └─→ emit('worker:task_completed')

4. 完成阶段（触发新调度）
   on('worker:task_completed')
       │
       ├─→ TaskDAG.markCompleted(taskId)
       ├─→ WorkerPool.setIdle(workerId)
       ├─→ tryAssignTasks()          ─→ 触发下一轮调度
       │
       └─→ 如果所有任务完成:
           ├─→ ReportGenerator.generate()
           ├─→ NotificationManager.notify()
           └─→ cleanup()
```

---

## Claude Code 2025 新能力整合

### Headless 模式

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
    PARALLELDEV_WORKER_ID: workerId,
    PARALLELDEV_TASK_ID: taskId,
    PARALLELDEV_MASTER_URL: masterUrl
  }
});
```

### Subagent 架构

| Agent | 用途 | Model |
|-------|-----|-------|
| task-orchestrator | 任务编排 | sonnet |
| quality-gate | 质量检查 | haiku |
| conflict-resolver | 冲突解决 | sonnet |
| worker-monitor | Worker 监控 | haiku |

### Skills 架构

| Skill | 触发条件 |
|-------|---------|
| parallel-executor | 用户提到 "parallel", "并行", "worktree" |
| conflict-resolution | 检测到 merge 冲突 |
| quality-assurance | 任务完成后、合并前 |
| frontend-development | 开发 React/Vue/Nuxt3 代码 |
| go-development | 开发 Go 1.23+ 代码 |
| java-development | 开发 Java JDK 17+ 代码 |
| typescript-development | 开发 TypeScript/Node.js 代码 |

---

## 6 层架构设计（严格遵循 README.md）

```
┌─────────────────────────────────────────────────────────────┐
│                  Layer 1: Task Management                   │
│  TaskDAG.ts | TaskScheduler.ts | TaskManager.ts             │
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
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│       Layer 4: Communication (Socket.IO + RPC)              │
│  SocketServer.ts | SocketClient.ts | StatusReporter.ts      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│       Layer 5: Quality Assurance (Subagent 驱动)            │
│  SubagentRunner.ts | ConflictResolver.ts | CodeValidator.ts │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Layer 6: Notification                     │
│  NotificationManager.ts | ReportGenerator.ts                │
└─────────────────────────────────────────────────────────────┘
```

---

## 完整文件结构

```
parallel-dev-mcp/
├── package.json
├── tsconfig.json
├── vitest.config.ts
├── CLAUDE.md
├── README.md
│
├── claude-task-master/              # Phase 0: 参考代码
│
├── src/
│   ├── cli-parallel.ts              # CLI 入口
│   └── parallel/
│       ├── index.ts
│       ├── types.ts
│       ├── config.ts
│       │
│       ├── task/                    # Layer 1
│       │   ├── TaskDAG.ts
│       │   ├── TaskScheduler.ts
│       │   └── TaskManager.ts
│       │
│       ├── master/                  # Layer 2
│       │   ├── MasterOrchestrator.ts
│       │   ├── WorkerPool.ts
│       │   └── StateManager.ts
│       │
│       ├── git/                     # Layer 3
│       │   ├── WorktreeManager.ts
│       │   └── ConflictDetector.ts
│       │
│       ├── tmux/                    # Layer 3
│       │   ├── TmuxController.ts
│       │   └── SessionMonitor.ts
│       │
│       ├── worker/                  # Layer 3+4
│       │   ├── TaskExecutor.ts
│       │   ├── WorkerAgent.ts
│       │   └── StatusReporter.ts
│       │
│       ├── communication/           # Layer 4
│       │   ├── SocketServer.ts
│       │   ├── SocketClient.ts
│       │   ├── RpcManager.ts
│       │   └── rpc-types.ts
│       │
│       ├── quality/                 # Layer 5
│       │   ├── SubagentRunner.ts
│       │   ├── ConflictResolver.ts
│       │   └── CodeValidator.ts
│       │
│       └── notification/            # Layer 6
│           ├── NotificationManager.ts
│           └── ReportGenerator.ts
│
├── paralleldev-plugin/              # Claude Code Plugin
│   ├── .claude-plugin/plugin.json
│   ├── commands/                    # 5 个斜杠命令
│   ├── agents/                      # 4 个 Agents
│   ├── skills/                      # 7 个 Skills
│   ├── hooks/hooks.json
│   ├── scripts/                     # 5 个脚本
│   └── .mcp.json
│
├── .paralleldev/                    # 运行状态
│   ├── state.json
│   └── config.json
│
├── .taskmaster/                     # 任务配置
│   └── tasks/
│       └── tasks.json.example
│
└── .claude/
    └── settings.json
```

---

## 执行顺序

1. **Phase -1**: 分支准备 → 提交推送
2. **Phase 0**: Pull 代码（task-master + Happy Socket.IO）
3. **Phase 1**: 基础设施 + Plugin 架构（13 个 TODO）
4. **Phase 2**: Layer 1 任务管理（3 个 TODO）
5. **Phase 3**: Layer 3 执行层（5 个 TODO）
6. **Phase 4**: Layer 4 通信层（4 个 TODO）
7. **Phase 5**: Layer 5 质量保证层（3 个 TODO）
8. **Phase 6**: Layer 2 编排层（3 个 TODO）
9. **Phase 7**: Layer 6 通知层（2 个 TODO）
10. **Phase 8**: 集成测试 + CLI（3 个 TODO）

---

## 最终验收标准

- [ ] 完整 6 层架构实现
- [ ] 所有 56+ TODO 完成
- [ ] TypeScript 编译无错误
- [ ] 所有单元测试通过
- [ ] Plugin 可在 Claude Code 中加载
- [ ] 端到端测试通过
- [ ] 文档更新完成

---

# 🔧 Phase 1 修复计划（优先执行）

> **问题来源**: 提交 `fd35804a278e51e6a97cd2fb26cd77126451b4c2` 中的 Phase 1 存在三大问题

## 问题分析

### 问题 1: Skills 不完善
**当前状态**: 每个 Skill 仅 22-41 行（评分 2/10）
**目标状态**: 遵循 `claude_template/` 模式，扩展到 200-300 行

**差距分析**:
| Skill | 当前行数 | 目标行数 | 缺失内容 |
|-------|----------|----------|----------|
| typescript-development | 24行 | 250行 | 命名规范、类型系统、代码质量标准、安全规则、代码模板 |
| frontend-development | 31行 | 300行 | React/Vue/Nuxt3详细规范、Tailwind CSS v4、组件模板、测试规范 |
| go-development | 22行 | 250行 | Go 1.23+规范、项目结构、测试表驱动、并发模式 |
| java-development | 22行 | 280行 | JDK 17+特性、Spring Boot 3.x规范、依赖注入、测试规范 |
| parallel-executor | 41行 | 200行 | Worktree详细操作、Tmux完整命令、Claude Headless完整参数 |
| conflict-resolution | 34行 | 180行 | 分层策略详细实现、AI辅助提示词、人工介入流程 |
| quality-assurance | 35行 | 180行 | 完整检查命令、CI/CD集成、质量门禁规则 |

### 问题 2: 依赖不完整
**当前 package.json 缺失的关键依赖**:

**🔴 CRITICAL（必须添加）**:
- `@anthropic-ai/claude-code`: Claude Code SDK - 核心依赖
- `@modelcontextprotocol/sdk`: MCP SDK - 协议支持
- `simple-git`: Git 操作库 - Worktree 管理

**🟡 IMPORTANT（强烈建议）**:
- `ts-node` / `tsx`: 运行时执行 TypeScript
- `chalk`: 终端颜色输出
- `dotenv`: 环境变量管理
- `fs-extra`: 增强文件系统操作
- `uuid`: 唯一 ID 生成

**🟢 RECOMMENDED（建议添加）**:
- `prettier`: 代码格式化
- `cross-spawn`: 跨平台子进程
- `inquirer`: 交互式命令行
- `ora`: 终端加载动画

### 问题 3: Agents 编排能力不足
**当前状态**: `task-orchestrator.md` 仅 36 行，缺乏状态机逻辑
**参考**: TaskMaster 的 `WorkflowOrchestrator` 有完整的 TDD 工作流

**需要添加的能力**:
1. 状态机设计（TDD: RED → GREEN → REFACTOR → COMMIT）
2. 阶段转换逻辑
3. 错误恢复机制
4. 并行任务协调
5. 质量门禁集成

---

## Phase 1 修复 TODO 清单

### TODO FIX-1.1: 扩展 Skills 文件（7个）

**目标**: 按照 `claude_template/` 模式扩展所有 Skill 文件

#### FIX-1.1.1: 扩展 `typescript-development/SKILL.md`

**参考文件**: `claude_template/CLAUDE.md`
**目标行数**: ~250 行

**必须包含的内容**:
```markdown
# TypeScript Development Skill

## 核心原则
- SOLID 原则
- DRY / KISS / YAGNI

## 类型系统规范
### 严格类型要求
- 禁止 `any`，使用 `unknown` 替代
- 启用 `strict: true`
- 使用 Zod 运行时验证

### 命名规范
- 接口: PascalCase (如 `TaskResult`)
- 函数: camelCase (如 `executeTask`)
- 常量: UPPER_SNAKE_CASE (如 `MAX_RETRIES`)
- 文件: kebab-case (如 `task-executor.ts`)

### 代码质量标准
- 函数不超过 50 行
- 所有函数必须有 JSDoc 注释
- 禁止行尾注释
- 每个文件单一职责

## 项目结构
- src/: 源码目录
- dist/: 编译输出
- tests/: 测试文件
- types/: 类型定义

## 错误处理
- try-catch 包裹异步操作
- 自定义错误类继承 Error
- 错误消息使用中文

## 测试规范
- 使用 Vitest
- 覆盖率 >80%
- 测试文件命名: *.test.ts

## 代码模板
[提供常用代码模板示例]
```

#### FIX-1.1.2: 扩展 `frontend-development/SKILL.md`

**参考文件**: `claude_template/CLAUDE_fronted.md` (1263行)
**目标行数**: ~300 行

**必须包含的内容**:
- Tailwind CSS v4 完整规范
- React 18+ Hooks 最佳实践
- Vue 3 Composition API 规范
- Nuxt 3 自动导入和文件路由
- 组件命名和目录结构
- 状态管理方案（Pinia/Zustand）
- 测试规范（Vitest + Testing Library）

#### FIX-1.1.3: 扩展 `go-development/SKILL.md`

**参考文件**: `claude_template/CLAUDE_GO.md` (283行)
**目标行数**: ~250 行

**必须包含的内容**:
- Go 1.23+ 新特性
- 项目结构（cmd/, internal/, pkg/）
- 错误处理模式
- 并发模式（goroutine, channel）
- 表驱动测试
- 依赖管理（go.mod）

#### FIX-1.1.4: 扩展 `java-development/SKILL.md`

**参考文件**: `claude_template/CLAUDE_java.md` (830行)
**目标行数**: ~280 行

**必须包含的内容**:
- JDK 17+ 特性（Records, Pattern Matching, Sealed Classes）
- Spring Boot 3.x 规范
- 依赖注入最佳实践
- JPA/Hibernate 规范
- 单元测试（JUnit 5 + Mockito）
- 代码风格和命名规范

#### FIX-1.1.5: 扩展 `parallel-executor/SKILL.md`

**目标行数**: ~200 行

**必须包含的内容**:
- Git Worktree 完整命令
  - `git worktree add/remove/list/prune`
  - 分支管理策略
- Tmux 会话管理
  - 完整命令参考
  - 输出捕获技巧
- Claude Headless 参数
  - `--output-format stream-json`
  - `--permission-mode` 选项
  - `--allowedTools` 配置

#### FIX-1.1.6: 扩展 `conflict-resolution/SKILL.md`

**目标行数**: ~180 行

**必须包含的内容**:
- Level 1 自动解决策略
  - lockfiles 处理
  - 格式化冲突处理
- Level 2 AI 辅助解决
  - 提示词模板
  - 上下文构建方法
- Level 3 人工介入流程
  - 通知机制
  - 冲突报告格式

#### FIX-1.1.7: 扩展 `quality-assurance/SKILL.md`

**目标行数**: ~180 行

**必须包含的内容**:
- TypeScript 检查命令
- ESLint 配置和规则
- Vitest 测试框架
- 覆盖率要求
- CI/CD 集成方案
- 质量门禁规则

---

### TODO FIX-1.2: 补全 package.json 依赖

**文件**: `package.json`

**依赖版本参考** (2025-12 最新):
- [@anthropic-ai/sdk](https://www.npmjs.com/package/@anthropic-ai/sdk): 0.71.2
- [@anthropic-ai/claude-agent-sdk](https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk): 0.1.0 (替代 claude-code)
- [@modelcontextprotocol/sdk](https://www.npmjs.com/package/@modelcontextprotocol/sdk): 2025.11.25 (日期版本)
- [simple-git](https://www.npmjs.com/package/simple-git): 3.30.0

**添加依赖**:
```json
{
  "dependencies": {
    "socket.io": "^4.7.0",
    "socket.io-client": "^4.7.0",
    "zod": "^3.22.0",
    "commander": "^11.0.0",
    "@anthropic-ai/sdk": "^0.71.2",
    "@anthropic-ai/claude-agent-sdk": "^0.1.0",
    "@modelcontextprotocol/sdk": "2025.11.25",
    "simple-git": "^3.30.0",
    "chalk": "^5.3.0",
    "dotenv": "^16.3.0",
    "fs-extra": "^11.2.0",
    "uuid": "^9.0.0",
    "ora": "^8.0.0",
    "inquirer": "^9.2.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/fs-extra": "^11.0.4",
    "@types/uuid": "^9.0.0",
    "@types/inquirer": "^9.0.0",
    "typescript": "^5.3.0",
    "vitest": "^1.0.0",
    "eslint": "^8.50.0",
    "@typescript-eslint/parser": "^6.0.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "ts-node": "^10.9.0",
    "tsx": "^4.7.0",
    "prettier": "^3.2.0",
    "cross-spawn": "^7.0.3"
  }
}
```

**注意**:
- `@anthropic-ai/claude-code` 已被重命名为 `@anthropic-ai/claude-agent-sdk`
- `@modelcontextprotocol/sdk` 使用日期版本格式

---

### TODO FIX-1.3: 增强 Agents 编排能力

#### FIX-1.3.1: 增强 `task-orchestrator.md`

**目标**: 引入 TaskMaster 的 WorkflowOrchestrator 状态机设计

**参考**: `claude-task-master/packages/tm-core/src/modules/workflow/orchestrators/workflow-orchestrator.ts`

**新增内容**:
```markdown
## 状态机设计

### TDD 工作流阶段
1. **RED**: 编写失败测试
2. **GREEN**: 实现最小通过代码
3. **REFACTOR**: 优化重构
4. **COMMIT**: 提交变更

### 阶段转换规则
- RED → GREEN: 测试编写完成
- GREEN → REFACTOR: 测试通过
- REFACTOR → COMMIT: 重构完成且测试仍通过
- COMMIT → RED: 开始下一个任务

### 错误恢复
- 测试失败: 回退到 GREEN 阶段
- 构建失败: 回退到 REFACTOR 阶段
- 冲突检测: 暂停并触发冲突解决

### 并行任务协调
- 最大并行任务数: 3
- 任务隔离: 独立 Worktree
- 状态同步: Socket.IO 事件

### 质量门禁
- TypeScript 编译通过
- ESLint 无错误
- 测试覆盖率 >80%
```

#### FIX-1.3.2: 增强 `quality-gate.md`

**新增内容**:
- 集成 SubagentRunner 调用逻辑
- 检查结果解析和报告
- 失败时的处理策略

#### FIX-1.3.3: 增强 `conflict-resolver.md`

**新增内容**:
- 分层解决策略的具体实现
- AI 辅助提示词模板
- 解决结果验证逻辑

#### FIX-1.3.4: 增强 `worker-monitor.md`

**新增内容**:
- 心跳检测间隔和阈值
- Worker 健康状态判断
- 异常 Worker 恢复策略

---

## 修复验收标准

- [ ] 所有 7 个 Skill 文件扩展到 180-300 行
- [ ] package.json 包含所有必需依赖
- [ ] `yarn install` 成功执行
- [ ] 所有 4 个 Agent 文件增强完成
- [ ] Agent 包含状态机设计和错误恢复逻辑
- [ ] TypeScript 编译无错误
- [ ] 提交修复到 feature/happy-clean 分支
