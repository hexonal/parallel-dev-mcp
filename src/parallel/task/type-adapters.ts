/**
 * 类型适配层
 * ParallelDev 类型 <-> tm-core 类型 双向转换
 */

import type {
  Task as TmCoreTask,
  TaskStatus as TmCoreTaskStatus,
  TaskPriority as TmCoreTaskPriority
} from '../tm-core';
import type { Task as ParallelDevTask, TaskStatus as ParallelDevTaskStatus } from '../types';

// ========== 状态映射 ==========

/**
 * ParallelDev → tm-core 状态映射
 */
const PARALLEL_TO_TMCORE_STATUS: Record<ParallelDevTaskStatus, TmCoreTaskStatus> = {
  pending: 'pending',
  ready: 'pending',
  running: 'in-progress',
  completed: 'done',
  failed: 'blocked',
  cancelled: 'cancelled'
};

/**
 * tm-core → ParallelDev 状态映射
 */
const TMCORE_TO_PARALLEL_STATUS: Record<TmCoreTaskStatus, ParallelDevTaskStatus> = {
  pending: 'pending',
  'in-progress': 'running',
  done: 'completed',
  blocked: 'failed',
  cancelled: 'cancelled',
  deferred: 'pending',
  review: 'running',
  completed: 'completed'
};

/**
 * 转换 ParallelDev 状态到 tm-core 状态
 */
export function toTmCoreStatus(status: ParallelDevTaskStatus): TmCoreTaskStatus {
  return PARALLEL_TO_TMCORE_STATUS[status] ?? 'pending';
}

/**
 * 转换 tm-core 状态到 ParallelDev 状态
 */
export function toParallelDevStatus(status: TmCoreTaskStatus): ParallelDevTaskStatus {
  return TMCORE_TO_PARALLEL_STATUS[status] ?? 'pending';
}

// ========== 优先级映射 ==========

/**
 * 数字优先级 → tm-core 优先级
 * ParallelDev: 1-5 (1最高)
 * tm-core: 'high' | 'medium' | 'low'
 */
export function toTmCorePriority(num: number): TmCoreTaskPriority {
  if (num <= 2) return 'high';
  if (num <= 3) return 'medium';
  return 'low';
}

/**
 * tm-core 优先级 → 数字优先级
 */
export function toNumericPriority(priority: TmCoreTaskPriority): number {
  switch (priority) {
    case 'high':
      return 1;
    case 'medium':
      return 3;
    case 'low':
      return 5;
    default:
      return 3;
  }
}

// ========== 任务转换 ==========

/**
 * ParallelDev Task → tm-core Task
 */
export function toTmCoreTask(task: ParallelDevTask): TmCoreTask {
  return {
    id: task.id,
    title: task.title,
    description: task.description,
    status: toTmCoreStatus(task.status),
    priority: toTmCorePriority(task.priority),
    dependencies: task.dependencies,
    subtasks: [],
    details: '',
    testStrategy: '',
    createdAt: task.createdAt,
    updatedAt: task.completedAt ?? task.startedAt ?? task.createdAt
  };
}

/**
 * tm-core Task → ParallelDev Task
 */
export function toParallelDevTask(task: TmCoreTask): ParallelDevTask {
  return {
    id: String(task.id),
    title: task.title,
    description: task.description ?? '',
    status: toParallelDevStatus(task.status),
    priority: toNumericPriority(task.priority),
    dependencies: task.dependencies?.map((d) => String(d)) ?? [],
    createdAt: task.createdAt ?? new Date().toISOString(),
    startedAt: task.status === 'in-progress' ? task.updatedAt : undefined,
    completedAt: task.status === 'done' ? task.updatedAt : undefined
  };
}

/**
 * 批量转换 ParallelDev Tasks → tm-core Tasks
 */
export function toTmCoreTasks(tasks: ParallelDevTask[]): TmCoreTask[] {
  return tasks.map(toTmCoreTask);
}

/**
 * 批量转换 tm-core Tasks → ParallelDev Tasks
 */
export function toParallelDevTasks(tasks: TmCoreTask[]): ParallelDevTask[] {
  return tasks.map(toParallelDevTask);
}

// ========== ID 转换 ==========

/**
 * 解析任务 ID 为数字
 * 支持格式: "task-1", "1", 1
 */
export function parseTaskId(id: string | number): number {
  if (typeof id === 'number') return id;
  const match = id.match(/(\d+)/);
  return match ? parseInt(match[1], 10) : 0;
}

/**
 * 格式化任务 ID 为字符串
 */
export function formatTaskId(id: number | string): string {
  if (typeof id === 'string') return id;
  return `task-${id}`;
}

// ========== 依赖转换 ==========

/**
 * 解析依赖字符串为数字数组
 * 支持格式: "1,2,3" | ["task-1", "task-2"] | [1, 2, 3]
 */
export function parseDependencies(
  deps: string | string[] | number[] | undefined
): number[] {
  if (!deps) return [];

  if (typeof deps === 'string') {
    return deps
      .split(',')
      .map((d) => d.trim())
      .filter(Boolean)
      .map(parseTaskId);
  }

  return deps.map(parseTaskId);
}

/**
 * 格式化依赖数组为字符串数组
 */
export function formatDependencies(deps: number[] | string[]): string[] {
  return deps.map(formatTaskId);
}

// ========== 类型守卫 ==========

/**
 * 检查是否为有效的 ParallelDev 状态
 */
export function isParallelDevStatus(status: string): status is ParallelDevTaskStatus {
  return ['pending', 'ready', 'running', 'completed', 'failed', 'cancelled'].includes(
    status
  );
}

/**
 * 检查是否为有效的 tm-core 状态
 */
export function isTmCoreStatus(status: string): status is TmCoreTaskStatus {
  return [
    'pending',
    'in-progress',
    'done',
    'blocked',
    'cancelled',
    'deferred',
    'review'
  ].includes(status);
}

/**
 * 检查是否为有效的 tm-core 优先级
 */
export function isTmCorePriority(priority: string): priority is TmCoreTaskPriority {
  return ['high', 'medium', 'low'].includes(priority);
}
