/**
 * Task Master 存储接口定义
 * 爆改自 claude-task-master/packages/tm-core/src/common/interfaces/storage.interface.ts
 * 移除 AI 方法（updateTaskWithPrompt, expandTaskWithPrompt）
 */

import type { Task, TaskMetadata, TaskStatus } from '../types';

/**
 * 加载任务选项
 */
export interface LoadTasksOptions {
  /** 按状态过滤 */
  status?: TaskStatus;
  /** 排除子任务（默认：false） */
  excludeSubtasks?: boolean;
}

/**
 * 更新状态结果
 */
export interface UpdateStatusResult {
  success: boolean;
  oldStatus: TaskStatus;
  newStatus: TaskStatus;
  taskId: string;
}

/**
 * 存储操作接口
 * 所有存储实现必须实现此接口
 */
export interface IStorage {
  /**
   * 加载所有任务，可按标签和其他条件过滤
   */
  loadTasks(tag?: string, options?: LoadTasksOptions): Promise<Task[]>;

  /**
   * 按 ID 加载单个任务
   */
  loadTask(taskId: string, tag?: string): Promise<Task | null>;

  /**
   * 保存任务到存储，替换现有任务
   */
  saveTasks(tasks: Task[], tag?: string): Promise<void>;

  /**
   * 追加新任务到现有存储
   */
  appendTasks(tasks: Task[], tag?: string): Promise<void>;

  /**
   * 按 ID 更新特定任务（直接结构更新）
   */
  updateTask(
    taskId: string,
    updates: Partial<Task>,
    tag?: string
  ): Promise<void>;

  /**
   * 按 ID 更新任务或子任务状态
   */
  updateTaskStatus(
    taskId: string,
    newStatus: TaskStatus,
    tag?: string
  ): Promise<UpdateStatusResult>;

  /**
   * 按 ID 删除任务
   */
  deleteTask(taskId: string, tag?: string): Promise<void>;

  /**
   * 检查给定标签的任务是否存在
   */
  exists(tag?: string): Promise<boolean>;

  /**
   * 加载任务集合元数据
   */
  loadMetadata(tag?: string): Promise<TaskMetadata | null>;

  /**
   * 保存任务集合元数据
   */
  saveMetadata(metadata: TaskMetadata, tag?: string): Promise<void>;

  /**
   * 获取存储中所有可用标签
   */
  getAllTags(): Promise<string[]>;

  /**
   * 创建新标签
   */
  createTag(
    tagName: string,
    options?: { copyFrom?: string; description?: string }
  ): Promise<void>;

  /**
   * 删除特定标签的所有任务和元数据
   */
  deleteTag(tag: string): Promise<void>;

  /**
   * 重命名标签
   */
  renameTag(oldTag: string, newTag: string): Promise<void>;

  /**
   * 复制所有任务从一个标签到另一个
   */
  copyTag(sourceTag: string, targetTag: string): Promise<void>;

  /**
   * 初始化存储
   */
  initialize(): Promise<void>;

  /**
   * 清理并关闭存储连接
   */
  close(): Promise<void>;

  /**
   * 获取存储统计
   */
  getStats(): Promise<StorageStats>;

  /**
   * 获取存储类型标识
   */
  getStorageType(): 'file';

  /**
   * 获取所有标签及其统计信息
   */
  getTagsWithStats(): Promise<TagsWithStatsResult>;
}

/**
 * 标签详细信息
 */
export interface TagInfo {
  /** 标签名 */
  name: string;
  /** 是否为当前/活动标签 */
  isCurrent: boolean;
  /** 该标签的任务总数 */
  taskCount: number;
  /** 已完成任务数 */
  completedTasks: number;
  /** 按状态分类的任务数 */
  statusBreakdown: Record<string, number>;
  /** 子任务计数 */
  subtaskCounts?: {
    totalSubtasks: number;
    subtasksByStatus: Record<string, number>;
  };
  /** 标签创建日期 */
  created?: string;
  /** 标签最后修改日期 */
  updatedAt?: string;
  /** 标签描述 */
  description?: string;
}

/**
 * getTagsWithStats 返回结果
 */
export interface TagsWithStatsResult {
  /** 带统计的标签列表 */
  tags: TagInfo[];
  /** 当前活动标签名 */
  currentTag: string | null;
  /** 标签总数 */
  totalTags: number;
}

/**
 * 存储统计接口
 */
export interface StorageStats {
  /** 所有标签的任务总数 */
  totalTasks: number;
  /** 标签总数 */
  totalTags: number;
  /** 存储大小（字节） */
  storageSize: number;
  /** 最后修改时间戳 */
  lastModified: string;
  /** 可用标签及任务计数 */
  tagStats: Array<{
    tag: string;
    taskCount: number;
    lastModified: string;
  }>;
}

/**
 * 存储配置选项
 */
export interface StorageConfig {
  /** 存储基础路径 */
  basePath: string;
  /** 启用备份 */
  enableBackup?: boolean;
  /** 最大备份数 */
  maxBackups?: number;
  /** 启用压缩 */
  enableCompression?: boolean;
  /** 文件编码（默认：utf8） */
  encoding?: BufferEncoding;
  /** 启用原子写入 */
  atomicWrites?: boolean;
}

/**
 * 存储实现基类
 */
export abstract class BaseStorage implements IStorage {
  protected config: StorageConfig;

  constructor(config: StorageConfig) {
    this.config = config;
  }

  // 抽象方法 - 必须由具体类实现
  abstract loadTasks(tag?: string, options?: LoadTasksOptions): Promise<Task[]>;
  abstract loadTask(taskId: string, tag?: string): Promise<Task | null>;
  abstract saveTasks(tasks: Task[], tag?: string): Promise<void>;
  abstract appendTasks(tasks: Task[], tag?: string): Promise<void>;
  abstract updateTask(
    taskId: string,
    updates: Partial<Task>,
    tag?: string
  ): Promise<void>;
  abstract updateTaskStatus(
    taskId: string,
    newStatus: TaskStatus,
    tag?: string
  ): Promise<UpdateStatusResult>;
  abstract deleteTask(taskId: string, tag?: string): Promise<void>;
  abstract exists(tag?: string): Promise<boolean>;
  abstract loadMetadata(tag?: string): Promise<TaskMetadata | null>;
  abstract saveMetadata(metadata: TaskMetadata, tag?: string): Promise<void>;
  abstract getAllTags(): Promise<string[]>;
  abstract createTag(
    tagName: string,
    options?: { copyFrom?: string; description?: string }
  ): Promise<void>;
  abstract deleteTag(tag: string): Promise<void>;
  abstract renameTag(oldTag: string, newTag: string): Promise<void>;
  abstract copyTag(sourceTag: string, targetTag: string): Promise<void>;
  abstract initialize(): Promise<void>;
  abstract close(): Promise<void>;
  abstract getStats(): Promise<StorageStats>;
  abstract getStorageType(): 'file';
  abstract getTagsWithStats(): Promise<TagsWithStatsResult>;

  /**
   * 生成备份文件名
   */
  protected generateBackupPath(originalPath: string): string {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const parts = originalPath.split('.');
    const extension = parts.pop();
    const baseName = parts.join('.');
    return `${baseName}.backup.${timestamp}.${extension}`;
  }

  /**
   * 验证任务数据
   */
  protected validateTask(task: Task): void {
    if (!task.id) {
      throw new Error('Task ID is required');
    }
    if (!task.title) {
      throw new Error('Task title is required');
    }
    if (!task.description) {
      throw new Error('Task description is required');
    }
    if (!task.status) {
      throw new Error('Task status is required');
    }
  }

  /**
   * 清理标签名（文件系统安全）
   */
  protected sanitizeTag(tag: string): string {
    return tag.replace(/[^a-zA-Z0-9-_]/g, '-').toLowerCase();
  }
}
