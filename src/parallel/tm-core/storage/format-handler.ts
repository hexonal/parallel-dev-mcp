/**
 * 任务存储文件格式处理器
 * 爆改自 claude-task-master/packages/tm-core/src/modules/storage/adapters/file-storage/format-handler.ts
 */

import type { Task, TaskMetadata } from '../common/types';

export interface FileStorageData {
  tasks: Task[];
  metadata: TaskMetadata;
}

export type FileFormat = 'legacy' | 'standard';

/**
 * 处理遗留格式和标准任务文件格式之间的检测和转换
 */
export class FormatHandler {
  /**
   * 检测原始数据的格式
   */
  detectFormat(data: unknown): FileFormat {
    if (!data || typeof data !== 'object') {
      return 'standard';
    }

    const keys = Object.keys(data);

    // 检查是否使用带标签键的遗留格式
    const hasLegacyFormat = keys.some(
      (key) => key !== 'tasks' && key !== 'metadata'
    );

    return hasLegacyFormat ? 'legacy' : 'standard';
  }

  /**
   * 从数据中提取指定标签的任务
   */
  extractTasks(data: unknown, tag: string): Task[] {
    if (!data) {
      return [];
    }

    const format = this.detectFormat(data);

    if (format === 'legacy') {
      return this.extractTasksFromLegacy(data as Record<string, unknown>, tag);
    }

    return this.extractTasksFromStandard(data as Record<string, unknown>);
  }

  /**
   * 从遗留格式提取任务
   */
  private extractTasksFromLegacy(
    data: Record<string, unknown>,
    tag: string
  ): Task[] {
    if (tag in data) {
      const tagData = data[tag] as { tasks?: Task[] } | undefined;
      return tagData?.tasks || [];
    }

    // 如果找不到请求的标签，尝试第一个可用标签
    const availableKeys = Object.keys(data).filter(
      (key) => key !== 'tasks' && key !== 'metadata'
    );
    if (tag === 'master' && availableKeys.length > 0) {
      const firstTag = availableKeys[0];
      const tagData = data[firstTag] as { tasks?: Task[] } | undefined;
      return tagData?.tasks || [];
    }

    return [];
  }

  /**
   * 从标准格式提取任务
   */
  private extractTasksFromStandard(data: Record<string, unknown>): Task[] {
    return (data?.tasks as Task[]) || [];
  }

  /**
   * 从数据中提取指定标签的元数据
   */
  extractMetadata(data: unknown, tag: string): TaskMetadata | null {
    if (!data) {
      return null;
    }

    const format = this.detectFormat(data);

    if (format === 'legacy') {
      return this.extractMetadataFromLegacy(
        data as Record<string, unknown>,
        tag
      );
    }

    return this.extractMetadataFromStandard(data as Record<string, unknown>);
  }

  /**
   * 从遗留格式提取元数据
   */
  private extractMetadataFromLegacy(
    data: Record<string, unknown>,
    tag: string
  ): TaskMetadata | null {
    if (tag in data) {
      const tagData = data[tag] as {
        metadata?: TaskMetadata;
        tasks?: Task[];
      } | undefined;

      if (!tagData?.metadata && tagData?.tasks) {
        return this.generateMetadataFromTasks(tagData.tasks, tag);
      }
      return tagData?.metadata || null;
    }

    const availableKeys = Object.keys(data).filter(
      (key) => key !== 'tasks' && key !== 'metadata'
    );
    if (tag === 'master' && availableKeys.length > 0) {
      const firstTag = availableKeys[0];
      const tagData = data[firstTag] as {
        metadata?: TaskMetadata;
        tasks?: Task[];
      } | undefined;

      if (!tagData?.metadata && tagData?.tasks) {
        return this.generateMetadataFromTasks(tagData.tasks, firstTag);
      }
      return tagData?.metadata || null;
    }

    return null;
  }

  /**
   * 从标准格式提取元数据
   */
  private extractMetadataFromStandard(
    data: Record<string, unknown>
  ): TaskMetadata | null {
    return (data?.metadata as TaskMetadata) || null;
  }

  /**
   * 从 tasks.json 文件中提取所有可用标签
   */
  extractTags(data: unknown): string[] {
    if (!data) {
      return [];
    }

    const format = this.detectFormat(data);

    if (format === 'legacy') {
      const keys = Object.keys(data as Record<string, unknown>);
      return keys.filter((key) => key !== 'tasks' && key !== 'metadata');
    }

    return ['master'];
  }

  /**
   * 将任务和元数据转换为适当的保存格式
   */
  convertToSaveFormat(
    tasks: Task[],
    metadata: TaskMetadata,
    existingData: unknown,
    tag: string
  ): unknown {
    const resolvedTag = tag || 'master';
    const normalizedTasks = this.normalizeTasks(tasks);

    if (existingData && this.detectFormat(existingData) === 'legacy') {
      return this.convertToLegacyFormat(normalizedTasks, metadata, resolvedTag);
    }

    return this.convertToStandardFormat(normalizedTasks, metadata, tag);
  }

  /**
   * 转换为遗留格式
   */
  private convertToLegacyFormat(
    tasks: Task[],
    metadata: TaskMetadata,
    tag: string
  ): unknown {
    return {
      [tag]: {
        tasks,
        metadata: {
          ...metadata,
          tags: [tag]
        }
      }
    };
  }

  /**
   * 转换为标准格式
   */
  private convertToStandardFormat(
    tasks: Task[],
    metadata: TaskMetadata,
    tag?: string
  ): FileStorageData {
    return {
      tasks,
      metadata: {
        ...metadata,
        tags: tag ? [tag] : []
      }
    };
  }

  /**
   * 规范化任务 ID - Task ID 为字符串，Subtask ID 为数字
   */
  private normalizeTasks(tasks: Task[]): Task[] {
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
   * 从任务生成元数据
   */
  private generateMetadataFromTasks(tasks: Task[], tag: string): TaskMetadata {
    return {
      version: '1.0.0',
      lastModified: new Date().toISOString(),
      taskCount: tasks.length,
      completedCount: tasks.filter((t) => t.status === 'done').length,
      tags: [tag]
    };
  }
}
