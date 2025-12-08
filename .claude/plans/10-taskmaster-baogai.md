# TaskMaster tm-core 爆改计划

## 用户选择
- **方案 B**：复制 tm-core 源码并爆改
- **全部任务功能**：TaskService + TaskExecutionService + Git 冲突检测 + 标签管理
- **纯文件系统**：移除 Supabase

---

## 一、目标目录结构

```
src/parallel/tm-core/
├── common/
│   ├── errors/task-master-error.ts
│   ├── interfaces/storage.interface.ts
│   ├── types/index.ts
│   ├── logger/
│   └── utils/
├── entities/task.entity.ts
├── storage/
│   ├── file-storage.ts
│   ├── file-operations.ts
│   ├── path-resolver.ts
│   └── format-handler.ts
├── services/
│   ├── task.service.ts
│   ├── task-execution.service.ts
│   └── tag.service.ts
├── git/
│   ├── git-domain.ts
│   └── git-adapter.ts
└── index.ts
```

---

## 二、文件复制清单

| 源文件 (tm-core) | 目标 | 修改 |
|------------------|------|------|
| `common/errors/task-master-error.ts` | `tm-core/common/errors/` | 直接复制 |
| `common/interfaces/storage.interface.ts` | `tm-core/common/interfaces/` | 移除 AI 方法 |
| `common/logger/*` | `tm-core/common/logger/` | 直接复制 |
| `common/utils/id-generator.ts` | `tm-core/common/utils/` | 直接复制 |
| `modules/tasks/entities/task.entity.ts` | `tm-core/entities/` | 直接复制 |
| `modules/storage/adapters/file-storage/*` | `tm-core/storage/` | 移除 ComplexityManager |
| `modules/tasks/services/task-service.ts` | `tm-core/services/` | 移除 AI/StorageFactory |
| `modules/tasks/services/task-execution-service.ts` | `tm-core/services/` | 直接复制 |
| `modules/tasks/services/tag.service.ts` | `tm-core/services/` | 直接复制 |
| `modules/git/git-domain.ts` | `tm-core/git/` | 直接复制 |
| `modules/git/adapters/git-adapter.ts` | `tm-core/git/` | 直接复制 |

---

## 三、移除的代码

### storage.interface.ts
```typescript
// 移除 AI 方法
- updateTaskWithPrompt(...)
- expandTaskWithPrompt(...)
```

### file-storage.ts
```typescript
// 移除
- ComplexityReportManager 导入和使用
- enrichTasksWithComplexity 方法
- updateTaskWithPrompt 改为抛出错误
- expandTaskWithPrompt 改为抛出错误
```

### task-service.ts
```typescript
// 移除
- StorageFactory 导入
- ExpandTaskResult 导入
- updateTaskWithPrompt 方法
- expandTaskWithPrompt 方法
// 修改
- initialize() 直接创建 FileStorage
```

### 完全不复制
- `modules/tasks/repositories/supabase/`
- `modules/storage/adapters/api-storage.ts`
- `modules/auth/`
- `modules/reports/`
- `modules/ai/`
- `modules/briefs/`

---

## 四、类型适配层

**新建 `src/parallel/task/type-adapters.ts`**

```typescript
// 状态映射
const STATUS_MAP = {
  'pending': 'pending',
  'ready': 'pending',
  'running': 'in-progress',
  'completed': 'done',
  'failed': 'blocked',
};

// 优先级映射
export function toTmCorePriority(num: number): TaskPriority;
export function toNumericPriority(priority: TaskPriority): number;
```

---

## 五、整合 TaskManager

**重写 `TaskManager.ts`**

```typescript
import { FileStorage } from '../tm-core/storage/file-storage';
import { TaskService } from '../tm-core/services/task.service';
import { TagService } from '../tm-core/services/tag.service';
import { TaskDAG } from './TaskDAG';  // 保留
import { TaskScheduler } from './TaskScheduler';  // 保留

export class TaskManager {
  private storage: FileStorage;
  private taskService: TaskService;
  private tagService: TagService;
  private dag: TaskDAG;  // 保留 ParallelDev 的 DAG
  private scheduler: TaskScheduler;  // 保留 ParallelDev 的调度器

  async loadTasks(): Promise<ParallelDevTask[]> {
    const tmCoreTasks = await this.storage.loadTasks();
    return tmCoreTasks.map(t => this.toParallelDevTask(t));
  }
}
```

**保留的 ParallelDev 代码**
- `TaskDAG.ts` - 保留（tm-core 没有 DAG 实现）
- `TaskScheduler.ts` - 保留（tm-core 没有调度器）

---

## 六、实施步骤

### Phase 1：复制和清理（~15 文件）
1. 创建 `src/parallel/tm-core/` 目录结构
2. 复制核心文件
3. 移除 Supabase/AI 代码
4. 修改导入路径（移除 `.js` 后缀）

### Phase 2：类型适配
1. 创建 `type-adapters.ts`
2. 创建简化版 `StorageFactory`
3. 扩展 `types.ts`

### Phase 3：整合 TaskManager
1. 重写 TaskManager 使用 tm-core FileStorage
2. 保持公共方法签名兼容
3. 保留 TaskDAG 和 TaskScheduler

### Phase 4：测试验证
1. 确保 84 个测试继续通过
2. 新增 FileStorage 单元测试
3. 新增类型适配测试

---

## 七、关键文件路径

**tm-core 源码**
- `claude-task-master/packages/tm-core/src/modules/storage/adapters/file-storage/file-storage.ts`
- `claude-task-master/packages/tm-core/src/common/interfaces/storage.interface.ts`
- `claude-task-master/packages/tm-core/src/modules/tasks/services/task-service.ts`

**ParallelDev 需修改**
- `src/parallel/task/TaskManager.ts`
- `src/parallel/types.ts`
