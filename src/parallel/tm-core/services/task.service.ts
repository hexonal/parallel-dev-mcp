/**
 * Task Service
 * 爆改自 claude-task-master/packages/tm-core/src/modules/tasks/services/task-service.ts
 * 移除 ConfigManager, StorageFactory, AI 方法
 */

import type { Task, TaskFilter, TaskStatus } from '../common/types';
import type { IStorage } from '../common/interfaces/storage.interface';
import { ERROR_CODES, TaskMasterError } from '../common/errors/task-master-error';
import { getLogger } from '../common/logger/factory';
import { TaskEntity } from '../entities/task.entity';
import { FileStorage } from '../storage/file-storage';

/**
 * 任务列表结果
 */
export interface TaskListResult {
  tasks: Task[];
  total: number;
  filtered: number;
  tag?: string;
  storageType: 'file';
}

/**
 * 获取任务列表选项
 */
export interface GetTaskListOptions {
  tag?: string;
  filter?: TaskFilter;
  includeSubtasks?: boolean;
}

/**
 * TaskService 处理所有任务相关操作
 * 简化版：直接使用 FileStorage，移除 AI 功能
 */
export class TaskService {
  private storage: IStorage;
  private initialized = false;
  private logger = getLogger('TaskService');
  private activeTag = 'master';
  private projectPath: string;

  constructor(projectPath: string) {
    this.projectPath = projectPath;
    this.storage = new FileStorage(projectPath);
  }

  /**
   * 初始化服务
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;
    await this.storage.initialize();
    this.initialized = true;
  }

  /**
   * 获取任务列表
   */
  async getTaskList(options: GetTaskListOptions = {}): Promise<TaskListResult> {
    const tag = options.tag || this.activeTag;

    try {
      const canPushStatusFilter =
        options.filter?.status &&
        !options.filter.priority &&
        !options.filter.tags &&
        !options.filter.assignee &&
        !options.filter.search &&
        options.filter.hasSubtasks === undefined;

      const storageOptions: { status?: TaskStatus; excludeSubtasks?: boolean } =
        {};

      if (canPushStatusFilter) {
        const statuses = Array.isArray(options.filter!.status)
          ? options.filter!.status
          : [options.filter!.status];
        if (statuses.length === 1) {
          storageOptions.status = statuses[0];
        }
      }

      if (options.includeSubtasks === false) {
        storageOptions.excludeSubtasks = true;
      }

      const rawTasks = await this.storage.loadTasks(tag, storageOptions);

      const baseOptions: { excludeSubtasks?: boolean } = {};
      if (options.includeSubtasks === false) {
        baseOptions.excludeSubtasks = true;
      }

      const allTasks =
        storageOptions.status !== undefined
          ? await this.storage.loadTasks(tag, baseOptions)
          : rawTasks;

      const taskEntities = TaskEntity.fromArray(rawTasks);

      let filteredEntities = taskEntities;
      if (options.filter && !canPushStatusFilter) {
        filteredEntities = this.applyFilters(taskEntities, options.filter);
      } else if (
        options.filter?.status &&
        Array.isArray(options.filter.status) &&
        options.filter.status.length > 1
      ) {
        filteredEntities = this.applyFilters(taskEntities, options.filter);
      }

      const tasks = filteredEntities.map((entity) => entity.toJSON());

      return {
        tasks,
        total: allTasks.length,
        filtered: filteredEntities.length,
        tag,
        storageType: 'file'
      };
    } catch (error) {
      if (error instanceof TaskMasterError) {
        throw error;
      }

      this.logger.error('Failed to get task list', error);
      throw new TaskMasterError(
        'Failed to get task list',
        ERROR_CODES.INTERNAL_ERROR,
        {
          operation: 'getTaskList',
          tag,
          hasFilter: !!options.filter
        },
        error as Error
      );
    }
  }

  /**
   * 按 ID 获取单个任务
   */
  async getTask(taskId: string, tag?: string): Promise<Task | null> {
    const activeTag = tag || this.activeTag;

    try {
      return await this.storage.loadTask(String(taskId), activeTag);
    } catch (error) {
      if (error instanceof TaskMasterError) {
        throw error;
      }

      throw new TaskMasterError(
        `Failed to get task ${taskId}`,
        ERROR_CODES.STORAGE_ERROR,
        {
          operation: 'getTask',
          resource: 'task',
          taskId: String(taskId),
          tag: activeTag
        },
        error as Error
      );
    }
  }

  /**
   * 按状态获取任务
   */
  async getTasksByStatus(
    status: TaskStatus | TaskStatus[],
    tag?: string
  ): Promise<Task[]> {
    const statuses = Array.isArray(status) ? status : [status];

    const result = await this.getTaskList({
      tag,
      filter: { status: statuses }
    });

    return result.tasks;
  }

  /**
   * 获取任务统计
   */
  async getTaskStats(tag?: string): Promise<{
    total: number;
    byStatus: Record<TaskStatus, number>;
    withSubtasks: number;
    blocked: number;
    storageType: 'file';
  }> {
    const result = await this.getTaskList({
      tag,
      includeSubtasks: true
    });

    const stats = {
      total: result.total,
      byStatus: {} as Record<TaskStatus, number>,
      withSubtasks: 0,
      blocked: 0,
      storageType: 'file' as const
    };

    const allStatuses: TaskStatus[] = [
      'pending',
      'in-progress',
      'done',
      'deferred',
      'cancelled',
      'blocked',
      'review'
    ];

    allStatuses.forEach((status) => {
      stats.byStatus[status] = 0;
    });

    result.tasks.forEach((task) => {
      stats.byStatus[task.status]++;

      if (task.subtasks && task.subtasks.length > 0) {
        stats.withSubtasks++;
      }

      if (task.status === 'blocked') {
        stats.blocked++;
      }
    });

    return stats;
  }

  /**
   * 获取下一个可用任务
   */
  async getNextTask(tag?: string): Promise<Task | null> {
    const result = await this.getTaskList({
      tag,
      filter: {
        status: ['pending', 'in-progress', 'done']
      }
    });

    const allTasks = result.tasks;
    const priorityValues = { critical: 4, high: 3, medium: 2, low: 1 };

    const toFullSubId = (
      parentId: string,
      maybeDotId: string | number
    ): string => {
      if (typeof maybeDotId === 'string' && maybeDotId.includes('.')) {
        return maybeDotId;
      }
      return `${parentId}.${maybeDotId}`;
    };

    const completedIds = new Set<string>();
    allTasks.forEach((t) => {
      if (t.status === 'done') {
        completedIds.add(String(t.id));
      }
      if (Array.isArray(t.subtasks)) {
        t.subtasks.forEach((st) => {
          if (st.status === 'done') {
            completedIds.add(`${t.id}.${st.id}`);
          }
        });
      }
    });

    // 1) 查找进行中父任务的可用子任务
    const candidateSubtasks: Array<Task & { parentId?: string }> = [];

    allTasks
      .filter((t) => t.status === 'in-progress' && Array.isArray(t.subtasks))
      .forEach((parent) => {
        parent.subtasks!.forEach((st) => {
          const stStatus = (st.status || 'pending').toLowerCase();
          if (stStatus !== 'pending' && stStatus !== 'in-progress') return;

          const fullDeps =
            st.dependencies?.map((d) => toFullSubId(String(parent.id), d)) ??
            [];
          const depsSatisfied =
            fullDeps.length === 0 ||
            fullDeps.every((depId) => completedIds.has(String(depId)));

          if (depsSatisfied) {
            candidateSubtasks.push({
              id: `${parent.id}.${st.id}`,
              title: st.title || `Subtask ${st.id}`,
              status: st.status || 'pending',
              priority: st.priority || parent.priority || 'medium',
              dependencies: fullDeps,
              parentId: String(parent.id),
              description: st.description,
              details: st.details,
              testStrategy: st.testStrategy,
              subtasks: []
            } as Task & { parentId: string });
          }
        });
      });

    if (candidateSubtasks.length > 0) {
      candidateSubtasks.sort((a, b) => {
        const pa =
          priorityValues[a.priority as keyof typeof priorityValues] ?? 2;
        const pb =
          priorityValues[b.priority as keyof typeof priorityValues] ?? 2;
        if (pb !== pa) return pb - pa;

        if (a.dependencies!.length !== b.dependencies!.length) {
          return a.dependencies!.length - b.dependencies!.length;
        }

        const [aPar, aSub] = String(a.id).split('.').map(Number);
        const [bPar, bSub] = String(b.id).split('.').map(Number);
        if (aPar !== bPar) return aPar - bPar;
        return aSub - bSub;
      });

      return candidateSubtasks[0];
    }

    // 2) 回退到顶级任务
    const eligibleTasks = allTasks.filter((task) => {
      const status = (task.status || 'pending').toLowerCase();
      if (status !== 'pending' && status !== 'in-progress') return false;

      const deps = task.dependencies ?? [];
      return deps.every((depId) => completedIds.has(String(depId)));
    });

    if (eligibleTasks.length === 0) return null;

    const nextTask = eligibleTasks.sort((a, b) => {
      const pa = priorityValues[a.priority as keyof typeof priorityValues] ?? 2;
      const pb = priorityValues[b.priority as keyof typeof priorityValues] ?? 2;
      if (pb !== pa) return pb - pa;

      const da = (a.dependencies ?? []).length;
      const db = (b.dependencies ?? []).length;
      if (da !== db) return da - db;

      return Number(a.id) - Number(b.id);
    })[0];

    return nextTask;
  }

  /**
   * 应用过滤器
   */
  private applyFilters(tasks: TaskEntity[], filter: TaskFilter): TaskEntity[] {
    return tasks.filter((task) => {
      if (filter.status) {
        const statuses = Array.isArray(filter.status)
          ? filter.status
          : [filter.status];
        if (!statuses.includes(task.status)) {
          return false;
        }
      }

      if (filter.priority) {
        const priorities = Array.isArray(filter.priority)
          ? filter.priority
          : [filter.priority];
        if (!priorities.includes(task.priority)) {
          return false;
        }
      }

      if (filter.tags && filter.tags.length > 0) {
        if (
          !task.tags ||
          !filter.tags.some((tag) => task.tags?.includes(tag))
        ) {
          return false;
        }
      }

      if (filter.assignee) {
        if (task.assignee !== filter.assignee) {
          return false;
        }
      }

      if (filter.search) {
        const searchLower = filter.search.toLowerCase();
        const inTitle = task.title.toLowerCase().includes(searchLower);
        const inDescription = task.description
          .toLowerCase()
          .includes(searchLower);
        const inDetails = task.details.toLowerCase().includes(searchLower);

        if (!inTitle && !inDescription && !inDetails) {
          return false;
        }
      }

      if (filter.hasSubtasks !== undefined) {
        const hasSubtasks = task.subtasks.length > 0;
        if (hasSubtasks !== filter.hasSubtasks) {
          return false;
        }
      }

      return true;
    });
  }

  /**
   * 获取存储类型
   */
  getStorageType(): 'file' {
    return 'file';
  }

  /**
   * 获取存储实例
   */
  getStorage(): IStorage {
    return this.storage;
  }

  /**
   * 获取当前活动标签
   */
  getActiveTag(): string {
    return this.activeTag;
  }

  /**
   * 设置活动标签
   */
  async setActiveTag(tag: string): Promise<void> {
    this.activeTag = tag;
  }

  /**
   * 更新任务
   */
  async updateTask(
    taskId: string | number,
    updates: Partial<Task>,
    tag?: string
  ): Promise<void> {
    if (!this.initialized) {
      await this.initialize();
    }

    const activeTag = tag || this.activeTag;
    const taskIdStr = String(taskId);

    try {
      await this.storage.updateTask(taskIdStr, updates, activeTag);
    } catch (error) {
      if (error instanceof TaskMasterError) {
        throw error;
      }

      throw new TaskMasterError(
        `Failed to update task ${taskId}`,
        ERROR_CODES.STORAGE_ERROR,
        {
          operation: 'updateTask',
          resource: 'task',
          taskId: taskIdStr,
          tag: activeTag
        },
        error as Error
      );
    }
  }

  /**
   * 更新任务状态
   */
  async updateTaskStatus(
    taskId: string | number,
    newStatus: TaskStatus,
    tag?: string
  ): Promise<{
    success: boolean;
    oldStatus: TaskStatus;
    newStatus: TaskStatus;
    taskId: string;
  }> {
    const activeTag = tag || this.activeTag;
    const taskIdStr = String(taskId);

    try {
      return await this.storage.updateTaskStatus(
        taskIdStr,
        newStatus,
        activeTag
      );
    } catch (error) {
      if (error instanceof TaskMasterError) {
        throw error;
      }

      throw new TaskMasterError(
        `Failed to update task status for ${taskIdStr}`,
        ERROR_CODES.STORAGE_ERROR,
        {
          operation: 'updateTaskStatus',
          resource: 'task',
          taskId: taskIdStr,
          newStatus,
          tag: activeTag
        },
        error as Error
      );
    }
  }

  /**
   * 获取带统计的标签
   */
  async getTagsWithStats() {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      return await this.storage.getTagsWithStats();
    } catch (error) {
      if (error instanceof TaskMasterError) {
        throw error;
      }

      throw new TaskMasterError(
        'Failed to get tags with stats',
        ERROR_CODES.STORAGE_ERROR,
        {
          operation: 'getTagsWithStats',
          resource: 'tags'
        },
        error as Error
      );
    }
  }

  /**
   * 关闭并清理资源
   */
  async close(): Promise<void> {
    if (this.storage) {
      await this.storage.close();
    }
    this.initialized = false;
  }
}
