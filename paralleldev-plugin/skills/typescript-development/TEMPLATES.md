# TypeScript 代码模板

## 目录
- [类模板](#类模板)
- [接口模板](#接口模板)
- [服务模板](#服务模板)
- [测试模板](#测试模板)
- [配置模板](#配置模板)

---

## 类模板

### 基础类

```typescript
/**
 * 类描述
 * @module module-name
 */

import type { Config, State } from './types';

/**
 * 类的详细描述
 */
export class ClassName {
  private readonly config: Config;
  private state: State;

  /**
   * 创建实例
   * @param config - 配置对象
   */
  constructor(config: Config) {
    this.config = config;
    this.state = this.initializeState();
  }

  /**
   * 公共方法描述
   * @param param - 参数描述
   * @returns 返回值描述
   */
  async publicMethod(param: ParamType): Promise<ReturnType> {
    // 1. 验证参数
    this.validateParam(param);

    // 2. 执行逻辑
    const result = await this.doSomething(param);

    // 3. 返回结果
    return this.formatResult(result);
  }

  /**
   * 私有方法
   */
  private validateParam(param: ParamType): void {
    if (!param) {
      throw new Error('参数不能为空');
    }
  }

  private initializeState(): State {
    return { /* 初始状态 */ };
  }
}
```

### 单例模式

```typescript
/**
 * 单例类
 */
export class Singleton {
  private static instance: Singleton | null = null;
  private readonly config: Config;

  private constructor(config: Config) {
    this.config = config;
  }

  /**
   * 获取单例实例
   */
  static getInstance(config?: Config): Singleton {
    if (!Singleton.instance) {
      if (!config) {
        throw new Error('首次调用必须提供配置');
      }
      Singleton.instance = new Singleton(config);
    }
    return Singleton.instance;
  }

  /**
   * 重置单例（仅用于测试）
   */
  static resetInstance(): void {
    Singleton.instance = null;
  }
}
```

---

## 接口模板

### 数据接口

```typescript
/**
 * 任务定义
 */
export interface Task {
  /** 任务唯一标识 */
  id: string;
  /** 任务标题 */
  title: string;
  /** 任务描述 */
  description: string;
  /** 当前状态 */
  status: TaskStatus;
  /** 依赖的任务 ID */
  dependencies: string[];
  /** 优先级 (1-5) */
  priority: number;
  /** 创建时间 */
  createdAt: string;
  /** 完成时间 */
  completedAt?: string;
  /** 错误信息 */
  error?: string;
}

/**
 * 任务状态
 */
export type TaskStatus =
  | 'pending'
  | 'ready'
  | 'running'
  | 'completed'
  | 'failed';

/**
 * 任务执行结果
 */
export interface TaskResult {
  /** 是否成功 */
  success: boolean;
  /** 输出内容 */
  output?: string;
  /** 错误信息 */
  error?: string;
  /** 执行时长（毫秒） */
  duration?: number;
}
```

### 服务接口

```typescript
/**
 * 任务服务接口
 */
export interface TaskService {
  /**
   * 创建任务
   */
  create(data: CreateTaskInput): Promise<Task>;

  /**
   * 获取任务
   */
  getById(id: string): Promise<Task | null>;

  /**
   * 更新任务
   */
  update(id: string, data: UpdateTaskInput): Promise<Task>;

  /**
   * 删除任务
   */
  delete(id: string): Promise<void>;

  /**
   * 列出所有任务
   */
  list(filter?: TaskFilter): Promise<Task[]>;
}

/**
 * 创建任务输入
 */
export interface CreateTaskInput {
  title: string;
  description?: string;
  dependencies?: string[];
  priority?: number;
}

/**
 * 更新任务输入
 */
export interface UpdateTaskInput {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: number;
}
```

---

## 服务模板

### 业务服务

```typescript
/**
 * 任务服务实现
 * @module services/TaskService
 */

import type { Task, TaskService, CreateTaskInput } from './types';

export class TaskServiceImpl implements TaskService {
  private readonly repository: TaskRepository;

  constructor(repository: TaskRepository) {
    this.repository = repository;
  }

  /**
   * 创建任务
   */
  async create(data: CreateTaskInput): Promise<Task> {
    // 1. 验证输入
    this.validateCreateInput(data);

    // 2. 构建任务对象
    const task: Task = {
      id: this.generateId(),
      title: data.title,
      description: data.description ?? '',
      status: 'pending',
      dependencies: data.dependencies ?? [],
      priority: data.priority ?? 3,
      createdAt: new Date().toISOString()
    };

    // 3. 保存
    await this.repository.save(task);

    // 4. 返回
    return task;
  }

  /**
   * 获取任务
   */
  async getById(id: string): Promise<Task | null> {
    return this.repository.findById(id);
  }

  private validateCreateInput(data: CreateTaskInput): void {
    if (!data.title?.trim()) {
      throw new Error('任务标题不能为空');
    }
  }

  private generateId(): string {
    return `task-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }
}
```

---

## 测试模板

### 单元测试

```typescript
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { TaskServiceImpl } from './TaskService';
import type { Task, TaskRepository } from './types';

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

// Mock Repository
function createMockRepository(): TaskRepository {
  return {
    save: vi.fn().mockResolvedValue(undefined),
    findById: vi.fn().mockResolvedValue(null),
    findAll: vi.fn().mockResolvedValue([]),
    delete: vi.fn().mockResolvedValue(undefined)
  };
}

describe('TaskServiceImpl', () => {
  let service: TaskServiceImpl;
  let mockRepo: TaskRepository;

  beforeEach(() => {
    mockRepo = createMockRepository();
    service = new TaskServiceImpl(mockRepo);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('create', () => {
    it('应该成功创建任务', async () => {
      const result = await service.create({ title: 'New Task' });

      expect(result.title).toBe('New Task');
      expect(result.status).toBe('pending');
      expect(mockRepo.save).toHaveBeenCalledOnce();
    });

    it('空标题应抛出错误', async () => {
      await expect(service.create({ title: '' }))
        .rejects.toThrow('任务标题不能为空');
    });
  });

  describe('getById', () => {
    it('存在的任务应返回任务对象', async () => {
      const task = createTestTask({ id: '123' });
      vi.mocked(mockRepo.findById).mockResolvedValue(task);

      const result = await service.getById('123');

      expect(result).toEqual(task);
    });

    it('不存在的任务应返回 null', async () => {
      const result = await service.getById('not-exist');

      expect(result).toBeNull();
    });
  });
});
```

---

## 配置模板

### 配置文件

```typescript
/**
 * 配置管理
 * @module config
 */

import { z } from 'zod';

/**
 * 配置 Schema
 */
const ConfigSchema = z.object({
  maxWorkers: z.number().min(1).max(10).default(3),
  timeout: z.number().min(1000).default(30000),
  retryCount: z.number().min(0).max(5).default(3),
  logLevel: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  git: z.object({
    mainBranch: z.string().default('main'),
    worktreeDir: z.string().default('.worktrees')
  }).default({})
});

export type Config = z.infer<typeof ConfigSchema>;

/**
 * 默认配置
 */
const DEFAULT_CONFIG: Config = {
  maxWorkers: 3,
  timeout: 30000,
  retryCount: 3,
  logLevel: 'info',
  git: {
    mainBranch: 'main',
    worktreeDir: '.worktrees'
  }
};

/**
 * 加载配置
 */
export function loadConfig(overrides: Partial<Config> = {}): Config {
  const merged = { ...DEFAULT_CONFIG, ...overrides };
  return ConfigSchema.parse(merged);
}

/**
 * 验证配置
 */
export function validateConfig(config: unknown): { valid: boolean; errors: string[] } {
  const result = ConfigSchema.safeParse(config);
  if (result.success) {
    return { valid: true, errors: [] };
  }
  return {
    valid: false,
    errors: result.error.errors.map(e => `${e.path.join('.')}: ${e.message}`)
  };
}
```

### 环境变量

```typescript
/**
 * 环境变量配置
 */

import { z } from 'zod';

const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  MAX_WORKERS: z.coerce.number().min(1).max(10).default(3),
  TIMEOUT_MS: z.coerce.number().min(1000).default(30000)
});

export type Env = z.infer<typeof EnvSchema>;

/**
 * 加载环境变量
 */
export function loadEnv(): Env {
  return EnvSchema.parse(process.env);
}
```
