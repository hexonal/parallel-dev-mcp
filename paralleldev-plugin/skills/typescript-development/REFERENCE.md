# TypeScript 详细参考

## 目录
- [类型系统](#类型系统)
- [命名规范完整](#命名规范完整)
- [函数命名约定](#函数命名约定)
- [错误处理详解](#错误处理详解)
- [测试规范](#测试规范)

---

## 类型系统

### tsconfig.json 完整配置

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictPropertyInitialization": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
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

### 泛型使用

```typescript
// 泛型函数
function parseJson<T>(json: string): T {
  return JSON.parse(json) as T;
}

// 泛型接口
interface Repository<T> {
  findById(id: string): Promise<T | null>;
  save(entity: T): Promise<T>;
  delete(id: string): Promise<void>;
}

// 泛型约束
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}
```

### 类型守卫

```typescript
// 类型谓词
function isTask(obj: unknown): obj is Task {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'title' in obj
  );
}

// 使用
function processItem(item: unknown) {
  if (isTask(item)) {
    console.log(item.title); // 类型安全
  }
}
```

### Zod 高级用法

```typescript
import { z } from 'zod';

// 复杂 Schema
const TaskSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1).max(200),
  description: z.string().optional(),
  status: z.enum(['pending', 'ready', 'running', 'completed', 'failed']),
  priority: z.number().min(1).max(5).default(3),
  dependencies: z.array(z.string()).default([]),
  assignedWorker: z.string().optional(),
  createdAt: z.string().datetime(),
  startedAt: z.string().datetime().optional(),
  completedAt: z.string().datetime().optional(),
  error: z.string().optional()
});

// 部分更新 Schema
const UpdateTaskSchema = TaskSchema.partial().omit({ id: true, createdAt: true });

// 从 Schema 导出类型
type Task = z.infer<typeof TaskSchema>;
type UpdateTask = z.infer<typeof UpdateTaskSchema>;

// 安全解析（不抛出错误）
function safeParseTask(data: unknown): Task | null {
  const result = TaskSchema.safeParse(data);
  return result.success ? result.data : null;
}
```

---

## 命名规范完整

### 标识符命名

| 类型 | 规范 | 正确示例 | 错误示例 |
|------|------|----------|----------|
| 接口 | PascalCase | `Task`, `TaskResult` | `task`, `ITask` |
| 类型别名 | PascalCase | `TaskStatus`, `WorkerConfig` | `taskStatus` |
| 类 | PascalCase | `TaskExecutor`, `WorktreeManager` | `taskExecutor` |
| 枚举 | PascalCase | `TaskStatus`, `ConflictLevel` | `TASK_STATUS` |
| 枚举值 | UPPER_SNAKE_CASE | `PENDING`, `IN_PROGRESS` | `pending` |
| 函数 | camelCase | `executeTask`, `getReadyTasks` | `ExecuteTask` |
| 方法 | camelCase | `addTask`, `removeWorker` | `AddTask` |
| 变量 | camelCase | `taskCount`, `isRunning` | `TaskCount` |
| 常量 | UPPER_SNAKE_CASE | `MAX_WORKERS`, `DEFAULT_TIMEOUT` | `maxWorkers` |
| 参数 | camelCase | `taskId`, `workerConfig` | `TaskId` |

### 文件命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 类文件 | PascalCase | `TaskExecutor.ts`, `WorktreeManager.ts` |
| 接口文件 | PascalCase 或 types | `Task.ts`, `types.ts` |
| 工具文件 | kebab-case | `string-utils.ts`, `date-helpers.ts` |
| 测试文件 | 同名 + .test | `TaskExecutor.test.ts` |
| 配置文件 | kebab-case | `config.ts`, `vitest.config.ts` |
| 常量文件 | kebab-case | `constants.ts` |
| 索引文件 | index | `index.ts` |

### 目录命名

```
src/
├── task/           # 小写，单数或复数均可
├── worker/
├── git/
├── tmux/
└── utils/          # 工具目录用复数
```

---

## 函数命名约定

```typescript
// 创建操作：create*
function createWorker(config: WorkerConfig): Worker { }
function createTask(title: string): Task { }

// 获取操作：get*
function getTask(id: string): Task | undefined { }
function getReadyTasks(): Task[] { }
function getAllWorkers(): Worker[] { }

// 查找操作：find*
function findTaskByTitle(title: string): Task | undefined { }
function findIdleWorker(): Worker | undefined { }

// 检查操作：is* / has* / can*
function isTaskReady(task: Task): boolean { }
function hasConflicts(worktree: Worktree): boolean { }
function canExecute(task: Task): boolean { }

// 设置操作：set*
function setTaskStatus(task: Task, status: TaskStatus): void { }
function setWorkerBusy(worker: Worker): void { }

// 添加操作：add*
function addTask(task: Task): void { }
function addDependency(taskId: string, depId: string): void { }

// 移除操作：remove*
function removeTask(id: string): boolean { }
function removeWorker(workerId: string): void { }

// 更新操作：update*
function updateTask(id: string, updates: Partial<Task>): Task { }

// 异步加载：load* / fetch*
async function loadTasks(): Promise<Task[]> { }
async function fetchWorkerStatus(): Promise<WorkerStatus> { }

// 异步保存：save* / persist*
async function saveState(): Promise<void> { }
async function persistTask(task: Task): Promise<void> { }

// 事件处理：on* / handle*
function onTaskCompleted(event: TaskEvent): void { }
function handleWorkerError(error: Error): void { }

// 转换操作：to* / from* / parse*
function toJson(task: Task): string { }
function fromJson(json: string): Task { }
function parseTaskFile(content: string): Task[] { }

// 验证操作：validate*
function validateTask(task: Task): ValidationResult { }
function validateConfig(config: Config): void { }

// 初始化：init* / initialize*
function initializeWorkerPool(): void { }
async function initDAG(tasks: Task[]): Promise<void> { }

// 清理：cleanup* / dispose* / destroy*
async function cleanup(): Promise<void> { }
function disposeResources(): void { }
```

---

## 错误处理详解

### 自定义错误类

```typescript
/**
 * 基础业务错误
 */
export class BusinessError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly cause?: Error
  ) {
    super(message);
    this.name = 'BusinessError';
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * 任务执行错误
 */
export class TaskExecutionError extends BusinessError {
  constructor(
    message: string,
    public readonly taskId: string,
    cause?: Error
  ) {
    super(message, 'TASK_EXECUTION_ERROR', cause);
    this.name = 'TaskExecutionError';
  }
}

/**
 * 验证错误
 */
export class ValidationError extends BusinessError {
  constructor(
    message: string,
    public readonly field: string,
    public readonly value: unknown
  ) {
    super(message, 'VALIDATION_ERROR');
    this.name = 'ValidationError';
  }
}
```

### 错误处理模式

```typescript
// 完整的错误处理流程
async function executeTask(task: Task): Promise<TaskResult> {
  const startTime = Date.now();

  try {
    // 1. 验证
    validateTask(task);

    // 2. 执行
    const output = await doExecute(task);

    // 3. 成功返回
    return {
      success: true,
      output,
      duration: Date.now() - startTime
    };

  } catch (error) {
    // 4. 记录错误
    console.error(`❌ 任务执行失败: ${task.id}`, error);

    // 5. 清理资源
    await cleanup(task).catch(cleanupError => {
      console.error('清理资源失败:', cleanupError);
    });

    // 6. 返回错误结果
    return {
      success: false,
      error: formatError(error),
      duration: Date.now() - startTime
    };
  }
}

// 错误格式化
function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}
```

---

## 测试规范

### Vitest 配置

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.test.ts', 'tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'dist/', '**/*.d.ts'],
      thresholds: {
        statements: 80,
        branches: 80,
        functions: 80,
        lines: 80
      }
    }
  }
});
```

### 测试文件结构

```typescript
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { TaskDAG } from './TaskDAG';
import type { Task } from './types';

// 测试辅助函数
function createTestTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'test-1',
    title: 'Test Task',
    description: '',
    status: 'pending',
    dependencies: [],
    priority: 3,
    createdAt: new Date().toISOString(),
    ...overrides
  };
}

describe('TaskDAG', () => {
  let dag: TaskDAG;

  beforeEach(() => {
    dag = new TaskDAG();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('addTask', () => {
    it('应该成功添加任务', () => {
      const task = createTestTask({ id: '1' });
      dag.addTask(task);
      expect(dag.getTask('1')).toEqual(task);
    });

    it('重复添加相同 ID 应抛出错误', () => {
      const task = createTestTask({ id: '1' });
      dag.addTask(task);
      expect(() => dag.addTask(task)).toThrow('任务 1 已存在');
    });

    it('添加带依赖的任务', () => {
      dag.addTask(createTestTask({ id: '1' }));
      dag.addTask(createTestTask({ id: '2', dependencies: ['1'] }));

      const task2 = dag.getTask('2');
      expect(task2?.dependencies).toContain('1');
    });
  });

  describe('getReadyTasks', () => {
    it('无依赖的任务应该立即可执行', () => {
      dag.addTask(createTestTask({ id: '1', dependencies: [] }));
      const ready = dag.getReadyTasks();
      expect(ready).toHaveLength(1);
      expect(ready[0].id).toBe('1');
    });

    it('有未完成依赖的任务不可执行', () => {
      dag.addTask(createTestTask({ id: '1' }));
      dag.addTask(createTestTask({ id: '2', dependencies: ['1'] }));

      const ready = dag.getReadyTasks();
      expect(ready).toHaveLength(1);
      expect(ready[0].id).toBe('1');
    });

    it('依赖完成后任务变为可执行', () => {
      dag.addTask(createTestTask({ id: '1' }));
      dag.addTask(createTestTask({ id: '2', dependencies: ['1'] }));

      dag.markCompleted('1');

      const ready = dag.getReadyTasks();
      expect(ready.map(t => t.id)).toContain('2');
    });
  });
});
```

### Mock 示例

```typescript
import { vi } from 'vitest';

// Mock 模块
vi.mock('./WorktreeManager', () => ({
  WorktreeManager: vi.fn().mockImplementation(() => ({
    create: vi.fn().mockResolvedValue({ path: '/tmp/worktree' }),
    remove: vi.fn().mockResolvedValue(undefined)
  }))
}));

// Mock 函数
const mockExecute = vi.fn().mockResolvedValue({ success: true });

// 验证调用
expect(mockExecute).toHaveBeenCalledWith(task);
expect(mockExecute).toHaveBeenCalledTimes(1);
```
