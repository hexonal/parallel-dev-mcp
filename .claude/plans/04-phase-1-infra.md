# Phase 1: 基础设施 + Claude Code Plugin

> 返回 [索引](00-index.md) | 上一篇: [验证策略](03-verification.md)

---

## TODO 完成规范

> **重要**：每个 TODO 小点完成后，执行以下流程：
> 1. 使用 task agent 进行自测验证
> 2. 询问用户是否提交推送代码
> 3. 如用户同意，执行 `git add -A && git commit && git push`

---

## 目标

建立项目骨架、核心类型、Plugin 架构

---

## TODO 1.1: 恢复项目基础配置

**步骤**：
```bash
# 1.1.1 创建 package.json
# 1.1.2 创建 tsconfig.json
# 1.1.3 创建 .gitignore
# 1.1.4 创建 vitest.config.ts
# 1.1.5 运行 yarn install 验证
```

**完成后**：task agent 自测（yarn install && yarn typecheck）→ 询问是否提交推送

---

## TODO 1.2: 创建核心类型定义 types.ts

**步骤**：
```bash
# 1.2.1 创建目录
mkdir -p src/parallel

# 1.2.2 创建 types.ts 文件
# 1.2.3 运行 tsc --noEmit 验证类型
```

**完成后**：task agent 自测（tsc --noEmit）→ 询问是否提交推送

---

## TODO 1.3: 创建 config.ts

**完成后**：task agent 自测（tsc --noEmit）→ 询问是否提交推送

---

## TODO 1.4: 创建 index.ts

**完成后**：task agent 自测（tsc --noEmit）→ 询问是否提交推送

---

## TODO 1.5: 创建运行状态目录模板

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

---

## TODO 1.6: 创建 Plugin 基础结构

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

---

## TODO 1.7: 创建 Plugin 斜杠命令（5个）

- `/pd:start` - 启动并行执行
- `/pd:status` - 查看状态
- `/pd:assign` - 手动分配任务
- `/pd:stop` - 停止执行
- `/pd:report` - 生成报告

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 1.8: 创建 Plugin Agents（4个）

- `task-orchestrator` - 任务编排专家
- `quality-gate` - 代码质量门禁
- `conflict-resolver` - Git 冲突解决专家
- `worker-monitor` - Worker 监控

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 1.9: 创建核心 Plugin Skills（3个）

- `parallel-executor` - 并行任务执行能力
- `conflict-resolution` - Git 冲突解决能力
- `quality-assurance` - 代码质量保证能力

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 1.10: 创建语言相关 Skills（4个）

- `frontend-development` - 前端开发规范
- `go-development` - Go 开发规范
- `java-development` - Java 开发规范
- `typescript-development` - TypeScript 开发规范

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 1.11: 创建 Plugin Hooks 和 MCP 配置

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 1.12: 创建 Plugin 支持脚本

- `master-start.sh` - 启动 Master
- `worker-start.sh` - 启动 Worker
- `cleanup.sh` - 清理资源
- `notify-change.sh` - 通知文件变更
- `task-completed.sh` - 通知任务完成

**完成后**：task agent 自测 → 询问是否提交推送

---

## TODO 1.13: 配置项目 .claude/ 目录

**完成后**：task agent 自测 → 询问是否提交推送

---

# Plugin 组件详细设计

> 本章节包含所有 Plugin 组件的详细设计规范

---

## Agents 设计规范（4个）

### 1. task-orchestrator - 任务编排专家

**配置**:
```yaml
name: task-orchestrator
model: sonnet
tools: [Read, Grep, Glob, Bash, Write, TodoWrite]
```

**核心职责**:
| 职责 | 描述 | 输出 |
|------|------|------|
| 依赖分析 | 构建任务依赖图 (DAG) | 依赖关系矩阵 |
| 并行识别 | 找出可并行执行的任务组 | 并行任务集合 |
| 顺序优化 | 关键路径分析、优先级排序 | 执行顺序列表 |
| 负载均衡 | 根据 Worker 数量分配任务 | Worker 分配方案 |

**输出格式 - 执行计划**:
```json
{
  "plan": {
    "id": "plan-xxx",
    "parallelGroups": [
      { "group": 1, "tasks": ["task-001", "task-003"], "canParallel": true },
      { "group": 2, "tasks": ["task-002"], "dependsOn": [1] }
    ],
    "criticalPath": ["task-001", "task-002"],
    "workerAssignment": { "worker-1": ["task-001"], "worker-2": ["task-003"] }
  }
}
```

**负载均衡算法**: LPT (Longest Processing Time First)

---

### 2. quality-gate - 代码质量门禁

**配置**:
```yaml
name: quality-gate
model: haiku
tools: [Bash, Read, Grep, Glob, Write]
```

**核心职责**:
| 职责 | 描述 | 阻止合并条件 |
|------|------|-------------|
| TypeScript 检查 | 静态类型安全 | 任何类型错误 |
| ESLint 检查 | 代码风格一致性 | error 级别错误 |
| E2E 测试 | 浏览器自动化验证 | 测试失败 |
| 单元测试 | 代码逻辑验证 | 覆盖率 < 阈值 |

**检查流程**:
```
任务完成 → TypeScript 检查 → ESLint 检查 → 单元测试 → E2E 测试 → 允许合并
           (失败阻止)     (失败阻止)    (失败阻止)   (失败阻止)
```

**检查命令**:
```bash
tsc --noEmit --pretty                    # TypeScript
eslint src --ext .ts,.tsx --format stylish  # ESLint
vitest run --coverage                    # 单元测试
# E2E 通过 Playwright MCP 执行
```

---

### 3. conflict-resolver - Git 冲突解决专家

**配置**:
```yaml
name: conflict-resolver
model: sonnet
tools: [Read, Edit, Bash, Grep, Glob, Write]
```

**分层解决策略**:
| 级别 | 策略 | 适用场景 |
|------|------|----------|
| Level 1 | 自动解决 | Lock 文件、配置文件 |
| Level 2 | AI 辅助 | 代码冲突、逻辑冲突 |
| Level 3 | 人工介入 | 安全敏感、复杂业务逻辑 |

**Level 1 自动解决**:
```bash
# Lock 文件
git checkout --ours package-lock.json && npm install
# 配置文件
git checkout --ours .prettierrc
```

**安全敏感文件识别**:
```
**/auth/**, **/security/**, **/crypto/**
**/*.key, **/*.pem, **/*password*, **/*token*
```

---

### 4. worker-monitor - Worker 监控专家

**配置**:
```yaml
name: worker-monitor
model: haiku
tools: [Bash, Read, Grep, Glob, Write]
```

**Worker 状态机**:
```
CREATED → IDLE ←→ BUSY → ERROR → RECOVERING → DEAD
           ↑_______________↓
```

**健康指标**:
| 指标 | 正常范围 | 异常阈值 |
|------|----------|----------|
| 心跳间隔 | < 30s | > 60s |
| 任务耗时 | < 估计 × 2 | > 估计 × 3 |
| 错误率 | < 5% | > 10% |

**监控命令**:
```bash
tmux list-sessions | grep "parallel-dev"  # 会话状态
cat .paralleldev/state.json | jq '.workers'  # Worker 状态
git worktree list --porcelain  # Worktree 状态
```

**恢复策略**:
| 故障类型 | 恢复策略 | 最大重试 |
|----------|----------|----------|
| 心跳超时 | 重启 tmux 会话 | 3 |
| 任务超时 | 取消 + 重新分配 | 2 |
| 进程崩溃 | 重建 Worker | 3 |

---

## Skills 设计规范（7个）

### 核心 Skills（3个）

#### 1. parallel-executor - 并行任务执行能力

**触发词**: parallel, 并行, worktree, worker, 任务执行, tmux, ParallelDev

**核心能力**:
| 能力 | 描述 |
|------|------|
| Git Worktree | 为每个任务创建独立工作目录 |
| Tmux 会话 | 管理并行执行的终端会话 |
| Claude Headless | 在隔离环境中执行 Claude Code |
| 任务调度 | 智能分配和监控任务 |

**Worktree 命令**:
```bash
git worktree add .worktrees/task-{id} -b task/{id}  # 创建
git worktree remove .worktrees/task-{id}            # 删除
git worktree list                                    # 列出
```

**Tmux 命令**:
```bash
tmux new-session -d -s parallel-dev-{id} -c /path   # 创建
tmux send-keys -t parallel-dev-{id} 'cmd' Enter     # 发送命令
tmux capture-pane -t parallel-dev-{id} -p           # 捕获输出
tmux kill-session -t parallel-dev-{id}              # 杀死
```

**Claude Headless**:
```bash
claude -p "prompt" --output-format stream-json
```

**任务生命周期**:
```
PENDING → ASSIGNED → RUNNING → DONE/FAILED
```

---

#### 2. conflict-resolution - Git 冲突解决能力

**触发词**: conflict, 冲突, merge, rebase, CONFLICT, 合并冲突

**分层策略**:
| 级别 | 策略 | 适用场景 |
|------|------|----------|
| Level 1 | 自动解决 | Lock 文件、配置文件 |
| Level 2 | AI 辅助 | 代码冲突 |
| Level 3 | 人工介入 | 安全敏感 |

**决策流程**:
```
冲突文件 → Lock 文件? → Level 1 (重新生成)
         → 配置文件? → Level 1 (保留 ours)
         → 安全敏感? → Level 3 (人工)
         → 普通代码 → Level 2 (AI 辅助)
```

---

#### 3. quality-assurance - 代码质量保证能力

**触发词**: 质量检查, quality, lint, typecheck, test, QA, 代码检查

**检查项目**:
| 检查类型 | 工具 | 用途 |
|----------|------|------|
| 类型检查 | TypeScript | 静态类型安全 |
| 代码规范 | ESLint | 代码风格一致性 |
| E2E 测试 | Playwright MCP | 浏览器自动化 |
| 格式化 | Prettier | 代码格式统一 |

**门禁流程**:
```
代码提交 → TypeScript → ESLint → E2E → 允许合并
```

---

### 语言 Skills（4个）

#### 4. frontend-development

**触发词**: 前端, frontend, React, Vue, Angular, CSS, Tailwind

**包含规范**:
- REACT.md - React 开发规范
- VUE.md - Vue 开发规范
- TAILWIND.md - Tailwind CSS 规范
- TEMPLATES.md - 组件模板
- E2E.md - 前端 E2E 测试

---

#### 5. go-development

**触发词**: Go, Golang, go mod

**包含规范**:
- REFERENCE.md - Go 开发参考
- TEMPLATES.md - Go 代码模板

---

#### 6. java-development

**触发词**: Java, Spring, Maven, Gradle

**包含规范**:
- REFERENCE.md - Java 开发参考
- TEMPLATES.md - Java 代码模板

---

#### 7. typescript-development

**触发词**: TypeScript, TS, Node.js, Deno

**包含规范**:
- REFERENCE.md - TypeScript 开发参考
- TEMPLATES.md - TS 代码模板

---

## Commands 设计规范（5个）

### /pd:start - 启动并行执行

**参数**:
| 参数 | 描述 | 必填 | 默认值 |
|------|------|------|--------|
| tasks | 任务文件路径 | 否 | .taskmaster/tasks/tasks.json |
| workers | Worker 数量 | 否 | 3 |

**执行步骤**:
1. 加载任务文件
2. 验证任务依赖图无循环
3. 启动指定数量 Worker
4. 开始事件驱动调度循环

**命令**:
```bash
node dist/cli-parallel.js run --tasks "${tasks}" --workers ${workers:-3}
```

---

### /pd:status - 查看状态

**输出内容**:
- Worker 状态（idle/busy/error）
- 任务进度（pending/running/completed/failed）
- 资源使用情况

**命令**:
```bash
node dist/cli-parallel.js status
```

---

### /pd:assign - 手动分配任务

**参数**:
| 参数 | 描述 | 必填 |
|------|------|------|
| taskId | 任务 ID | 是 |
| workerId | Worker ID | 是 |

**命令**:
```bash
node dist/cli-parallel.js assign --task "${taskId}" --worker "${workerId}"
```

---

### /pd:stop - 停止执行

**参数**:
| 参数 | 描述 | 必填 |
|------|------|------|
| force | 强制停止（不等待当前任务完成） | 否 |

**命令**:
```bash
node dist/cli-parallel.js stop ${force:+--force}
```

---

### /pd:report - 生成报告

**参数**:
| 参数 | 描述 | 必填 | 默认值 |
|------|------|------|--------|
| format | 输出格式 | 否 | markdown |

**命令**:
```bash
node dist/cli-parallel.js report --format "${format:-markdown}"
```

---

## Hooks 和 MCP 配置

### Hooks 配置 (hooks/hooks.json)

```json
{
  "hooks": [
    {
      "event": "PostToolUse",
      "matcher": { "tool": "Edit" },
      "command": "bash scripts/notify-change.sh \"$FILE_PATH\""
    },
    {
      "event": "PostToolUse",
      "matcher": { "tool": "Write" },
      "command": "bash scripts/notify-change.sh \"$FILE_PATH\""
    },
    {
      "event": "Stop",
      "command": "bash scripts/task-completed.sh"
    }
  ]
}
```

**Hook 触发说明**:
| 事件 | 触发条件 | 执行脚本 |
|------|----------|----------|
| PostToolUse (Edit) | 文件编辑后 | notify-change.sh |
| PostToolUse (Write) | 文件写入后 | notify-change.sh |
| Stop | 会话结束时 | task-completed.sh |

---

### MCP 配置 (.mcp.json)

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

---

## Scripts 设计规范（5个）

| 脚本 | 用途 | 触发场景 |
|------|------|----------|
| master-start.sh | 启动 Master 控制进程 | /pd:start |
| worker-start.sh | 启动 Worker 执行进程 | Worker 初始化 |
| cleanup.sh | 清理 Worktree/Tmux 资源 | 任务完成/失败 |
| notify-change.sh | 通知文件变更给 Master | PostToolUse Hook |
| task-completed.sh | 通知任务完成 | Stop Hook |

---

## Phase 1 验收标准

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

## 需求满足追溯

| 需求 | 实现文件 | 验证方法 |
|------|----------|----------|
| R0.1 | `types.ts` | 类型检查通过 |
| R0.2 | `config.ts` | 配置加载测试 |
| R0.3 | `.paralleldev/` | 目录存在性检查 |
| R0.4 | `paralleldev-plugin/` | Plugin 结构验证 |

---

## 快速导航

- ← [验证策略](03-verification.md)
- → [Phase 2: Layer 1 任务管理](05-phase-2-task.md)
- [返回索引](00-index.md)
