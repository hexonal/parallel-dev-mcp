# Phase -1/0：准备 + 源码分析

> 返回 [索引](00-index.md)

> 本阶段是所有后续工作的前置条件

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

### TODO 0.1: Clone task-master 仓库

**步骤**：
```bash
# 0.1.1 执行 clone
git clone https://github.com/eyaltoledano/claude-task-master.git ./claude-task-master

# 0.1.2 验证 clone 成功
ls -la ./claude-task-master

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

---

## 源码分析结果

> ✅ 已完成探索

### task-master 核心架构发现

| 组件 | 状态 | 说明 |
|------|------|------|
| TaskDAG | ❌ 不存在独立类 | 依赖管理在 `dependency-manager.js` |
| TaskScheduler | ❌ 不存在独立类 | 调度逻辑在 `task-service.ts` |
| WorkflowOrchestrator | ✅ 核心 | TDD 状态机（RED-GREEN-COMMIT）|
| Direct Functions | ✅ 最有价值 | 41 个核心业务函数 |
| MCP 工具 | ✅ 43 个工具 | 完整的 Claude 集成 |

### 需要爆改的文件列表

| 组件 | 源文件路径 | 行数 | 核心功能 |
|------|----------|------|----------|
| 循环依赖检测 | `dependency-manager.js:379-429` | 50 | `isCircularDependency()` |
| 依赖验证 | `dependency-manager.js:436-527` | 90 | `validateTaskDependencies()` |
| 下一个任务算法 | `task-service.ts:299-418` | 120 | `getNextTask()` |
| Task 类型定义 | `common/types/index.ts` | - | Task, TaskStatus, TaskPriority |
| tasks.json 格式 | `.taskmaster/tasks/tasks.json.example` | - | 任务文件格式 |

### 必须融合的组件

#### Direct Functions
```
claude-task-master/mcp-server/src/core/direct-functions/
├── parse-prd.js          ← PRD → 任务列表
├── expand-task.js        ← 任务 → 子任务
├── add-task.js           ← AI 生成任务
├── analyze-task-complexity.js  ← 复杂度分析
├── next-task.js          ← 下一个任务算法
└── update-tasks.js       ← 批量更新
```

#### 状态机
```
claude-task-master/packages/tm-core/src/modules/workflow/
├── orchestrators/workflow-orchestrator.ts  ← TDD 状态机
├── managers/workflow-state-manager.ts      ← 状态持久化
└── services/workflow.service.ts            ← 工作流服务
```

### ⚠️ 重要发现

- task-master **没有独立的 TaskDAG 类**，依赖管理在 `dependency-manager.js` 中
- `modules/dependencies/` 是占位符（TODO: Migrate from scripts/modules/）
- 需要从 JS 代码提取并转换为 TypeScript

---

## Phase 0 验收标准

- [ ] `./claude-task-master` 目录存在且包含源码
- [ ] 完成源码结构分析
- [ ] 记录需要爆改的文件列表

---

## 快速导航

- ← [返回索引](00-index.md)
- → [爆改设计方案](02-design.md)
