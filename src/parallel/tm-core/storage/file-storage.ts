/**
 * 文件存储实现
 * 爆改自 claude-task-master/packages/tm-core/src/modules/storage/adapters/file-storage/file-storage.ts
 * 移除 ComplexityManager 和 AI 相关方法
 */

import path from 'node:path';
import {
  ERROR_CODES,
  TaskMasterError
} from '../common/errors/task-master-error';
import type {
  IStorage,
  LoadTasksOptions,
  StorageStats,
  TagsWithStatsResult,
  UpdateStatusResult
} from '../common/interfaces/storage.interface';
import type { Task, TaskMetadata, TaskStatus } from '../common/types';
import { FileOperations } from './file-operations';
import { FormatHandler } from './format-handler';
import { PathResolver } from './path-resolver';

/**
 * 基于文件的存储实现，使用单一 tasks.json 文件
 */
export class FileStorage implements IStorage {
  private formatHandler: FormatHandler;
  private fileOps: FileOperations;
  private pathResolver: PathResolver;

  constructor(projectPath: string) {
    this.formatHandler = new FormatHandler();
    this.fileOps = new FileOperations();
    this.pathResolver = new PathResolver(projectPath);
  }

  /**
   * 初始化存储，创建必要的目录
   */
  async initialize(): Promise<void> {
    await this.fileOps.ensureDir(this.pathResolver.getTasksDir());
  }

  /**
   * 关闭存储并清理资源
   */
  async close(): Promise<void> {
    await this.fileOps.cleanup();
  }

  /**
   * 获取存储类型
   */
  getStorageType(): 'file' {
    return 'file';
  }

  /**
   * 获取存储统计信息
   */
  async getStats(): Promise<StorageStats> {
    const filePath = this.pathResolver.getTasksPath();

    try {
      const stats = await this.fileOps.getStats(filePath);
      const data = await this.fileOps.readJson(filePath);
      const tags = this.formatHandler.extractTags(data);

      let totalTasks = 0;
      const tagStats = tags.map((tag) => {
        const tasks = this.formatHandler.extractTasks(data, tag);
        const taskCount = tasks.length;
        totalTasks += taskCount;

        return {
          tag,
          taskCount,
          lastModified: stats.mtime.toISOString()
        };
      });

      return {
        totalTasks,
        totalTags: tags.length,
        lastModified: stats.mtime.toISOString(),
        storageSize: stats.size,
        tagStats
      };
    } catch (error: unknown) {
      const err = error as NodeJS.ErrnoException;
      if (err.code === 'ENOENT') {
        return {
          totalTasks: 0,
          totalTags: 0,
          lastModified: new Date().toISOString(),
          storageSize: 0,
          tagStats: []
        };
      }
      throw new Error(`Failed to get storage stats: ${err.message}`);
    }
  }

  /**
   * 从 tasks.json 文件加载任务
   */
  async loadTasks(tag?: string, options?: LoadTasksOptions): Promise<Task[]> {
    const filePath = this.pathResolver.getTasksPath();
    const resolvedTag = tag || 'master';

    try {
      const rawData = await this.fileOps.readJson(filePath);
      let tasks = this.formatHandler.extractTasks(rawData, resolvedTag);

      if (options) {
        if (options.status) {
          tasks = tasks.filter((task) => task.status === options.status);
        }

        if (options.excludeSubtasks) {
          tasks = tasks.map((task) => ({
            ...task,
            subtasks: []
          }));
        }
      }

      return tasks;
    } catch (error: unknown) {
      const err = error as NodeJS.ErrnoException;
      if (err.code === 'ENOENT') {
        return [];
      }
      throw new Error(`Failed to load tasks: ${err.message}`);
    }
  }

  /**
   * 按 ID 加载单个任务
   * 支持任务和子任务（点号表示法如 "1.2"）
   */
  async loadTask(taskId: string, tag?: string): Promise<Task | null> {
    const tasks = await this.loadTasks(tag);

    // 检查是否为子任务
    if (taskId.includes('.')) {
      const [parentId, subtaskId] = taskId.split('.');
      const parentTask = tasks.find((t) => String(t.id) === parentId);

      if (!parentTask || !parentTask.subtasks) {
        return null;
      }

      const subtask = parentTask.subtasks.find(
        (st) => String(st.id) === subtaskId
      );
      if (!subtask) {
        return null;
      }

      const toFullSubId = (maybeDotId: string | number): string => {
        const depId = String(maybeDotId);
        return depId.includes('.') ? depId : `${parentTask.id}.${depId}`;
      };
      const resolvedDependencies =
        subtask.dependencies?.map((dep) => toFullSubId(dep)) ?? [];

      // 返回子任务的 Task 对象
      const subtaskResult = {
        ...subtask,
        id: taskId,
        title: subtask.title || `Subtask ${subtaskId}`,
        description: subtask.description || '',
        status: subtask.status || 'pending',
        priority: subtask.priority || parentTask.priority || 'medium',
        dependencies: resolvedDependencies,
        details: subtask.details || '',
        testStrategy: subtask.testStrategy || '',
        subtasks: [],
        tags: parentTask.tags || [],
        assignee: subtask.assignee || parentTask.assignee,
        complexity: subtask.complexity || parentTask.complexity,
        createdAt: subtask.createdAt || parentTask.createdAt,
        updatedAt: subtask.updatedAt || parentTask.updatedAt
      };

      return subtaskResult as Task;
    }

    return tasks.find((task) => String(task.id) === String(taskId)) || null;
  }

  /**
   * 为特定标签保存任务
   */
  async saveTasks(tasks: Task[], tag?: string): Promise<void> {
    const filePath = this.pathResolver.getTasksPath();
    const resolvedTag = tag || 'master';

    await this.fileOps.ensureDir(this.pathResolver.getTasksDir());

    let existingData: Record<string, unknown> = {};
    try {
      existingData = (await this.fileOps.readJson(filePath)) as Record<
        string,
        unknown
      >;
    } catch (error: unknown) {
      const err = error as NodeJS.ErrnoException;
      if (err.code !== 'ENOENT') {
        throw new Error(`Failed to read existing tasks: ${err.message}`);
      }
    }

    const metadata: TaskMetadata = {
      version: '1.0.0',
      lastModified: new Date().toISOString(),
      taskCount: tasks.length,
      completedCount: tasks.filter((t) => t.status === 'done').length,
      tags: [resolvedTag]
    };

    const normalizedTasks = this.normalizeTaskIds(tasks);

    if (
      this.formatHandler.detectFormat(existingData) === 'legacy' ||
      Object.keys(existingData).some(
        (key) => key !== 'tasks' && key !== 'metadata'
      )
    ) {
      existingData[resolvedTag] = {
        tasks: normalizedTasks,
        metadata
      };
    } else if (resolvedTag === 'master') {
      existingData = {
        tasks: normalizedTasks,
        metadata
      };
    } else {
      const masterTasks = (existingData.tasks as Task[]) || [];
      const masterMetadata = (existingData.metadata as TaskMetadata) || metadata;

      existingData = {
        master: {
          tasks: masterTasks,
          metadata: masterMetadata
        },
        [resolvedTag]: {
          tasks: normalizedTasks,
          metadata
        }
      };
    }

    await this.fileOps.writeJson(filePath, existingData);
  }

  /**
   * 规范化任务 ID
   */
  private normalizeTaskIds(tasks: Task[]): Task[] {
    return tasks.map((task) => ({
      ...task,
      id: String(task.id),
      dependencies: task.dependencies?.map((dep) => String(dep)) || [],
      subtasks:
        task.subtasks?.map((subtask) => ({
          ...subtask,
          id: Number(subtask.id),
          parentId: String(subtask.parentId)
        })) || []
    }));
  }

  /**
   * 检查任务文件是否存在
   */
  async exists(_tag?: string): Promise<boolean> {
    const filePath = this.pathResolver.getTasksPath();
    return this.fileOps.exists(filePath);
  }

  /**
   * 获取所有可用标签
   */
  async getAllTags(): Promise<string[]> {
    try {
      const filePath = this.pathResolver.getTasksPath();
      const data = await this.fileOps.readJson(filePath);
      return this.formatHandler.extractTags(data);
    } catch (error: unknown) {
      const err = error as NodeJS.ErrnoException;
      if (err.code === 'ENOENT') {
        return [];
      }
      throw new Error(`Failed to get tags: ${err.message}`);
    }
  }

  /**
   * 加载元数据
   */
  async loadMetadata(tag?: string): Promise<TaskMetadata | null> {
    const filePath = this.pathResolver.getTasksPath();
    const resolvedTag = tag || 'master';

    try {
      const rawData = await this.fileOps.readJson(filePath);
      return this.formatHandler.extractMetadata(rawData, resolvedTag);
    } catch (error: unknown) {
      const err = error as NodeJS.ErrnoException;
      if (err.code === 'ENOENT') {
        return null;
      }
      throw new Error(`Failed to load metadata: ${err.message}`);
    }
  }

  /**
   * 保存元数据
   */
  async saveMetadata(_metadata: TaskMetadata, tag?: string): Promise<void> {
    const tasks = await this.loadTasks(tag);
    await this.saveTasks(tasks, tag);
  }

  /**
   * 追加任务到现有存储
   */
  async appendTasks(tasks: Task[], tag?: string): Promise<void> {
    const existingTasks = await this.loadTasks(tag);
    const allTasks = [...existingTasks, ...tasks];
    await this.saveTasks(allTasks, tag);
  }

  /**
   * 更新特定任务
   */
  async updateTask(
    taskId: string,
    updates: Partial<Task>,
    tag?: string
  ): Promise<void> {
    const tasks = await this.loadTasks(tag);
    const taskIndex = tasks.findIndex((t) => String(t.id) === String(taskId));

    if (taskIndex === -1) {
      throw new Error(`Task ${taskId} not found`);
    }

    tasks[taskIndex] = {
      ...tasks[taskIndex],
      ...updates,
      id: String(taskId)
    };
    await this.saveTasks(tasks, tag);
  }

  /**
   * 更新任务或子任务状态
   */
  async updateTaskStatus(
    taskId: string,
    newStatus: TaskStatus,
    tag?: string
  ): Promise<UpdateStatusResult> {
    const tasks = await this.loadTasks(tag);

    // 检查是否为子任务
    if (taskId.includes('.')) {
      return this.updateSubtaskStatusInFile(tasks, taskId, newStatus, tag);
    }

    const taskIndex = tasks.findIndex((t) => String(t.id) === String(taskId));

    if (taskIndex === -1) {
      throw new Error(`Task ${taskId} not found`);
    }

    const oldStatus = tasks[taskIndex].status;
    if (oldStatus === newStatus) {
      return {
        success: true,
        oldStatus,
        newStatus,
        taskId: String(taskId)
      };
    }

    tasks[taskIndex] = {
      ...tasks[taskIndex],
      status: newStatus,
      updatedAt: new Date().toISOString()
    };

    await this.saveTasks(tasks, tag);

    return {
      success: true,
      oldStatus,
      newStatus,
      taskId: String(taskId)
    };
  }

  /**
   * 更新子任务状态
   */
  private async updateSubtaskStatusInFile(
    tasks: Task[],
    subtaskId: string,
    newStatus: TaskStatus,
    tag?: string
  ): Promise<UpdateStatusResult> {
    const parts = subtaskId.split('.');
    if (parts.length !== 2) {
      throw new Error(
        `Invalid subtask ID format: ${subtaskId}. Expected format: parentId.subtaskId`
      );
    }

    const [parentId, subIdRaw] = parts;
    const subId = subIdRaw.trim();
    if (!/^\d+$/.test(subId)) {
      throw new Error(
        `Invalid subtask ID: ${subId}. Subtask ID must be a positive integer.`
      );
    }
    const subtaskNumericId = Number(subId);

    const parentTaskIndex = tasks.findIndex(
      (t) => String(t.id) === String(parentId)
    );

    if (parentTaskIndex === -1) {
      throw new Error(`Parent task ${parentId} not found`);
    }

    const parentTask = tasks[parentTaskIndex];
    const subtaskIndex = parentTask.subtasks.findIndex(
      (st) => st.id === subtaskNumericId || String(st.id) === subId
    );

    if (subtaskIndex === -1) {
      throw new Error(
        `Subtask ${subtaskId} not found in parent task ${parentId}`
      );
    }

    const oldStatus = parentTask.subtasks[subtaskIndex].status || 'pending';
    if (oldStatus === newStatus) {
      return {
        success: true,
        oldStatus,
        newStatus,
        taskId: subtaskId
      };
    }

    const now = new Date().toISOString();

    parentTask.subtasks[subtaskIndex] = {
      ...parentTask.subtasks[subtaskIndex],
      status: newStatus,
      updatedAt: now
    };

    // 根据子任务状态自动调整父任务状态
    const subs = parentTask.subtasks;
    let parentNewStatus = parentTask.status;
    if (subs.length > 0) {
      const norm = (s: { status?: TaskStatus }) => s.status || 'pending';
      const isDoneLike = (s: { status?: TaskStatus }) => {
        const st = norm(s);
        return st === 'done' || st === 'completed';
      };
      const allDone = subs.every(isDoneLike);
      const anyInProgress = subs.some((s) => norm(s) === 'in-progress');
      const anyDone = subs.some(isDoneLike);
      const allPending = subs.every((s) => norm(s) === 'pending');

      if (allDone) parentNewStatus = 'done';
      else if (anyInProgress || anyDone) parentNewStatus = 'in-progress';
      else if (allPending) parentNewStatus = 'pending';
    }

    tasks[parentTaskIndex] = {
      ...parentTask,
      ...(parentNewStatus !== parentTask.status
        ? { status: parentNewStatus }
        : {}),
      updatedAt: now
    };

    await this.saveTasks(tasks, tag);

    return {
      success: true,
      oldStatus,
      newStatus,
      taskId: subtaskId
    };
  }

  /**
   * 删除任务
   */
  async deleteTask(taskId: string, tag?: string): Promise<void> {
    const tasks = await this.loadTasks(tag);
    const filteredTasks = tasks.filter((t) => String(t.id) !== String(taskId));

    if (filteredTasks.length === tasks.length) {
      throw new Error(`Task ${taskId} not found`);
    }

    await this.saveTasks(filteredTasks, tag);
  }

  /**
   * 创建新标签
   */
  async createTag(
    tagName: string,
    options?: { copyFrom?: string; description?: string }
  ): Promise<void> {
    const filePath = this.pathResolver.getTasksPath();

    try {
      const existingData = (await this.fileOps.readJson(filePath)) as Record<
        string,
        unknown
      >;
      const format = this.formatHandler.detectFormat(existingData);

      if (format === 'legacy') {
        if (tagName in existingData) {
          throw new TaskMasterError(
            `Tag ${tagName} already exists`,
            ERROR_CODES.VALIDATION_ERROR
          );
        }

        let tasksToCopy: Task[] = [];
        if (options?.copyFrom) {
          const sourceData = existingData[options.copyFrom] as {
            tasks?: Task[];
          };
          if (sourceData?.tasks) {
            tasksToCopy = JSON.parse(JSON.stringify(sourceData.tasks));
          }
        }

        existingData[tagName] = {
          tasks: tasksToCopy,
          metadata: {
            created: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            description:
              options?.description ||
              `Tag created on ${new Date().toLocaleDateString()}`,
            tags: [tagName]
          }
        };

        await this.fileOps.writeJson(filePath, existingData);
      } else {
        const masterTasks = (existingData.tasks as Task[]) || [];
        const masterMetadata = existingData.metadata || {};

        let tasksToCopy: Task[] = [];
        if (options?.copyFrom === 'master' || !options?.copyFrom) {
          tasksToCopy = JSON.parse(JSON.stringify(masterTasks));
        }

        const newData = {
          master: {
            tasks: masterTasks,
            metadata: { ...masterMetadata, tags: ['master'] }
          },
          [tagName]: {
            tasks: tasksToCopy,
            metadata: {
              created: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              description:
                options?.description ||
                `Tag created on ${new Date().toLocaleDateString()}`,
              tags: [tagName]
            }
          }
        };

        await this.fileOps.writeJson(filePath, newData);
      }
    } catch (error: unknown) {
      const err = error as NodeJS.ErrnoException;
      if (err.code === 'ENOENT') {
        throw new Error('Tasks file not found - initialize project first');
      }
      throw error;
    }
  }

  /**
   * 删除标签
   */
  async deleteTag(tag: string): Promise<void> {
    const filePath = this.pathResolver.getTasksPath();

    try {
      const existingData = (await this.fileOps.readJson(filePath)) as Record<
        string,
        unknown
      >;

      if (this.formatHandler.detectFormat(existingData) === 'legacy') {
        if (tag in existingData) {
          delete existingData[tag];
          await this.fileOps.writeJson(filePath, existingData);
        } else {
          throw new Error(`Tag ${tag} not found`);
        }
      } else if (tag === 'master') {
        await this.fileOps.deleteFile(filePath);
      } else {
        throw new Error(`Tag ${tag} not found in standard format`);
      }
    } catch (error: unknown) {
      const err = error as NodeJS.ErrnoException;
      if (err.code === 'ENOENT') {
        throw new Error(`Tag ${tag} not found - file doesn't exist`);
      }
      throw error;
    }
  }

  /**
   * 重命名标签
   */
  async renameTag(oldTag: string, newTag: string): Promise<void> {
    const filePath = this.pathResolver.getTasksPath();

    try {
      const existingData = (await this.fileOps.readJson(filePath)) as Record<
        string,
        unknown
      >;

      if (this.formatHandler.detectFormat(existingData) === 'legacy') {
        if (oldTag in existingData) {
          existingData[newTag] = existingData[oldTag];
          delete existingData[oldTag];

          const tagData = existingData[newTag] as {
            metadata?: { tags?: string[] };
          };
          if (tagData.metadata) {
            tagData.metadata.tags = [newTag];
          }

          await this.fileOps.writeJson(filePath, existingData);
        } else {
          throw new Error(`Tag ${oldTag} not found`);
        }
      } else if (oldTag === 'master') {
        const masterTasks = (existingData.tasks as Task[]) || [];
        const masterMetadata = existingData.metadata || {};

        const newData = {
          [newTag]: {
            tasks: masterTasks,
            metadata: { ...masterMetadata, tags: [newTag] }
          }
        };

        await this.fileOps.writeJson(filePath, newData);
      } else {
        throw new Error(`Tag ${oldTag} not found in standard format`);
      }
    } catch (error: unknown) {
      const err = error as NodeJS.ErrnoException;
      if (err.code === 'ENOENT') {
        throw new Error(`Tag ${oldTag} not found - file doesn't exist`);
      }
      throw error;
    }
  }

  /**
   * 复制标签
   */
  async copyTag(sourceTag: string, targetTag: string): Promise<void> {
    const tasks = await this.loadTasks(sourceTag);

    if (tasks.length === 0) {
      throw new Error(`Source tag ${sourceTag} not found or has no tasks`);
    }

    await this.saveTasks(tasks, targetTag);
  }

  /**
   * 获取带统计信息的所有标签
   */
  async getTagsWithStats(): Promise<TagsWithStatsResult> {
    const availableTags = await this.getAllTags();
    const activeTag = await this.getActiveTagFromState();

    const tagsWithStats = await Promise.all(
      availableTags.map(async (tagName) => {
        try {
          const tasks = await this.loadTasks(tagName);
          const statusBreakdown: Record<string, number> = {};
          let completedTasks = 0;

          const subtaskCounts = {
            totalSubtasks: 0,
            subtasksByStatus: {} as Record<string, number>
          };

          tasks.forEach((task) => {
            const status = task.status || 'pending';
            statusBreakdown[status] = (statusBreakdown[status] || 0) + 1;

            if (status === 'done') {
              completedTasks++;
            }

            if (task.subtasks && task.subtasks.length > 0) {
              subtaskCounts.totalSubtasks += task.subtasks.length;

              task.subtasks.forEach((subtask) => {
                const subStatus = subtask.status || 'pending';
                subtaskCounts.subtasksByStatus[subStatus] =
                  (subtaskCounts.subtasksByStatus[subStatus] || 0) + 1;
              });
            }
          });

          const metadata = await this.loadMetadata(tagName);

          return {
            name: tagName,
            isCurrent: tagName === activeTag,
            taskCount: tasks.length,
            completedTasks,
            statusBreakdown,
            subtaskCounts:
              subtaskCounts.totalSubtasks > 0 ? subtaskCounts : undefined,
            created: metadata?.created,
            description: metadata?.description
          };
        } catch {
          return {
            name: tagName,
            isCurrent: tagName === activeTag,
            taskCount: 0,
            completedTasks: 0,
            statusBreakdown: {}
          };
        }
      })
    );

    return {
      tags: tagsWithStats,
      currentTag: activeTag,
      totalTags: tagsWithStats.length
    };
  }

  /**
   * 从 state.json 获取活动标签
   */
  private async getActiveTagFromState(): Promise<string> {
    try {
      const statePath = path.join(
        this.pathResolver.getBasePath(),
        'state.json'
      );
      const stateData = (await this.fileOps.readJson(statePath)) as {
        currentTag?: string;
      };
      return stateData?.currentTag || 'master';
    } catch {
      return 'master';
    }
  }
}

export default FileStorage;
