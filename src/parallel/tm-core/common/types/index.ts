/**
 * Task Master 核心类型定义
 * 爆改自 claude-task-master/packages/tm-core/src/common/types/index.ts
 * 移除 API 存储类型，仅保留文件存储
 */

// ============================================================================
// Type Literals
// ============================================================================

/**
 * 存储类型 - 仅支持文件存储
 */
export type StorageType = 'file';

/**
 * 任务状态
 */
export type TaskStatus =
  | 'pending'
  | 'in-progress'
  | 'done'
  | 'deferred'
  | 'cancelled'
  | 'blocked'
  | 'review'
  | 'completed';

/**
 * 任务优先级
 */
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';

/**
 * 任务复杂度
 */
export type TaskComplexity = 'simple' | 'moderate' | 'complex' | 'very-complex';

// ============================================================================
// Core Interfaces
// ============================================================================

/**
 * 占位任务接口（用于临时/最小任务对象）
 */
export interface PlaceholderTask {
  id: string;
  title: string;
  status: TaskStatus;
  priority: TaskPriority;
}

/**
 * 基础任务接口
 */
export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  dependencies: string[];
  details: string;
  testStrategy: string;
  subtasks: Subtask[];

  // 可选增强属性
  createdAt?: string;
  updatedAt?: string;
  effort?: number;
  actualEffort?: number;
  tags?: string[];
  assignee?: string;

  // 复杂度分析（来自复杂度报告）
  complexity?: TaskComplexity | number;
  recommendedSubtasks?: number;
  expansionPrompt?: string;
  complexityReasoning?: string;
}

/**
 * 子任务接口
 * ID 可以是数字或字符串
 */
export interface Subtask extends Omit<Task, 'id' | 'subtasks'> {
  id: number | string;
  parentId: string;
  subtasks?: never;
}

/**
 * 任务元数据
 */
export interface TaskMetadata {
  version: string;
  lastModified: string;
  taskCount: number;
  completedCount: number;
  projectName?: string;
  description?: string;
  tags?: string[];
  created?: string;
  updated?: string;
}

/**
 * 任务集合
 */
export interface TaskCollection {
  tasks: Task[];
  metadata: TaskMetadata;
}

/**
 * 任务标签
 */
export interface TaskTag {
  name: string;
  tasks: string[];
  metadata: Record<string, unknown>;
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * 创建任务类型（不包含生成字段）
 */
export type CreateTask = Omit<
  Task,
  'id' | 'createdAt' | 'updatedAt' | 'subtasks'
> & {
  subtasks?: Omit<Subtask, 'id' | 'parentId' | 'createdAt' | 'updatedAt'>[];
};

/**
 * 更新任务类型（除 ID 外所有字段可选）
 */
export type UpdateTask = Partial<Omit<Task, 'id'>> & {
  id: string;
};

/**
 * 任务过滤器
 */
export interface TaskFilter {
  status?: TaskStatus | TaskStatus[];
  priority?: TaskPriority | TaskPriority[];
  tags?: string[];
  hasSubtasks?: boolean;
  search?: string;
  assignee?: string;
}

/**
 * 排序选项
 */
export interface TaskSortOptions {
  field: keyof Task;
  direction: 'asc' | 'desc';
}

// ============================================================================
// Type Guards
// ============================================================================

/**
 * 检查值是否为有效的 TaskStatus
 */
export function isTaskStatus(value: unknown): value is TaskStatus {
  return (
    typeof value === 'string' &&
    [
      'pending',
      'in-progress',
      'done',
      'deferred',
      'cancelled',
      'blocked',
      'review',
      'completed'
    ].includes(value)
  );
}

/**
 * 检查值是否为有效的 TaskPriority
 */
export function isTaskPriority(value: unknown): value is TaskPriority {
  return (
    typeof value === 'string' &&
    ['low', 'medium', 'high', 'critical'].includes(value)
  );
}

/**
 * 检查值是否为有效的 TaskComplexity
 */
export function isTaskComplexity(value: unknown): value is TaskComplexity {
  return (
    typeof value === 'string' &&
    ['simple', 'moderate', 'complex', 'very-complex'].includes(value)
  );
}

/**
 * 检查对象是否为 Task
 */
export function isTask(obj: unknown): obj is Task {
  if (!obj || typeof obj !== 'object') return false;
  const task = obj as Record<string, unknown>;

  return (
    typeof task.id === 'string' &&
    typeof task.title === 'string' &&
    typeof task.description === 'string' &&
    isTaskStatus(task.status) &&
    isTaskPriority(task.priority) &&
    Array.isArray(task.dependencies) &&
    typeof task.details === 'string' &&
    typeof task.testStrategy === 'string' &&
    Array.isArray(task.subtasks)
  );
}

/**
 * 检查对象是否为 Subtask
 */
export function isSubtask(obj: unknown): obj is Subtask {
  if (!obj || typeof obj !== 'object') return false;
  const subtask = obj as Record<string, unknown>;

  return (
    (typeof subtask.id === 'number' || typeof subtask.id === 'string') &&
    typeof subtask.parentId === 'string' &&
    typeof subtask.title === 'string' &&
    typeof subtask.description === 'string' &&
    isTaskStatus(subtask.status) &&
    isTaskPriority(subtask.priority) &&
    !('subtasks' in subtask)
  );
}
