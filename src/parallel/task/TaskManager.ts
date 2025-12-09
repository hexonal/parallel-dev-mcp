/**
 * 任务管理器
 * @module parallel/task/TaskManager
 *
 * 集成 tm-core FileStorage + ParallelDev DAG/Scheduler + AI 能力
 */

import { Task, SchedulingStrategy, ParallelDevConfig } from '../types';
import {
  FileStorage,
  TaskService,
  TagService,
  TaskAIService,
  TaskExecutionService,
  type AIConfig,
  type AIResponse,
  type ParsePRDOptions,
  type ExpandTaskOptions,
  type StartTaskOptions,
  type StartTaskResult,
  type ConflictCheckResult
} from '../tm-core';
import { TaskDAG } from './TaskDAG';
import { TaskScheduler } from './TaskScheduler';
import {
  toParallelDevTask,
  toParallelDevTasks,
  toTmCoreTask,
  toTmCoreStatus
} from './type-adapters';

/**
 * TaskManager 整合 tm-core 存储 + ParallelDev DAG/调度器 + AI 能力
 */
export class TaskManager {
  private projectRoot: string;
  private storage: FileStorage;
  private taskService: TaskService;
  private tagService: TagService;
  private taskExecutionService: TaskExecutionService;
  private taskAIService: TaskAIService | null = null;
  private dag: TaskDAG;
  private scheduler: TaskScheduler;
  private currentTag?: string;

  /**
   * 创建任务管理器
   * @param projectRoot 项目根目录
   * @param config 配置对象
   */
  constructor(projectRoot: string, config: ParallelDevConfig) {
    this.projectRoot = projectRoot;
    this.storage = new FileStorage(projectRoot);
    this.taskService = new TaskService(projectRoot);
    this.tagService = new TagService(this.storage);
    this.taskExecutionService = new TaskExecutionService(this.taskService);
    this.dag = new TaskDAG();
    this.scheduler = new TaskScheduler(this.dag, config.schedulingStrategy);
  }

  /**
   * 初始化服务
   */
  async initialize(): Promise<void> {
    await this.taskService.initialize();
  }

  /**
   * 检查任务文件是否存在
   * @param tag 可选标签
   * @returns 是否存在
   */
  async tasksFileExists(tag?: string): Promise<boolean> {
    try {
      const tasks = await this.storage.loadTasks(tag);
      return tasks.length > 0;
    } catch {
      return false;
    }
  }

  /**
   * 加载任务文件
   * @param tag 可选标签
   * @returns 任务数组
   */
  async loadTasks(tag?: string): Promise<Task[]> {
    this.currentTag = tag;

    // 使用 tm-core FileStorage 加载
    const tmCoreTasks = await this.storage.loadTasks(tag);

    // 转换为 ParallelDev 格式
    const tasks = toParallelDevTasks(tmCoreTasks);

    // 重新初始化 DAG
    this.dag = new TaskDAG();
    this.dag.addTasks(tasks);

    // 更新调度器的 DAG 引用
    this.scheduler = new TaskScheduler(this.dag, this.scheduler.getStrategy());

    // 检测循环依赖
    if (this.dag.hasCycle()) {
      throw new Error('任务存在循环依赖');
    }

    return this.dag.getAllTasks();
  }

  /**
   * 保存任务状态到文件
   */
  async saveTasks(): Promise<void> {
    const tasks = this.dag.getAllTasks();

    // 转换并保存每个任务
    for (const task of tasks) {
      const tmCoreTask = toTmCoreTask(task);
      await this.storage.updateTask(String(tmCoreTask.id), tmCoreTask, this.currentTag);
    }
  }

  /**
   * 验证单个任务
   * @param task 任务对象
   * @returns 验证结果
   */
  validateTask(task: Partial<Task>): {
    valid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    if (!task.id || task.id.trim() === '') {
      errors.push('任务 ID 不能为空');
    }

    if (!task.title || task.title.trim() === '') {
      errors.push('任务标题不能为空');
    }

    if (task.priority !== undefined) {
      if (task.priority < 1 || task.priority > 5) {
        errors.push('优先级必须在 1-5 之间');
      }
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * 获取 DAG 实例
   */
  getDAG(): TaskDAG {
    return this.dag;
  }

  /**
   * 获取调度器实例
   */
  getScheduler(): TaskScheduler {
    return this.scheduler;
  }

  /**
   * 获取可执行任务
   */
  getReadyTasks(): Task[] {
    return this.dag.getReadyTasks();
  }

  /**
   * 调度下一批任务
   * @param maxWorkers 最大 Worker 数量
   */
  scheduleNextBatch(maxWorkers: number): Task[] {
    return this.scheduler.getParallelTasks(maxWorkers);
  }

  /**
   * 标记任务开始执行
   */
  markTaskStarted(taskId: string, workerId: string): void {
    this.dag.markRunning(taskId, workerId);
  }

  /**
   * 标记任务完成
   */
  async markTaskCompleted(taskId: string): Promise<void> {
    this.dag.markCompleted(taskId);

    // 同步到 tm-core storage
    await this.storage.updateTask(taskId, { status: 'done' }, this.currentTag);
  }

  /**
   * 标记任务失败
   */
  async markTaskFailed(taskId: string, error: string): Promise<void> {
    this.dag.markFailed(taskId, error);

    // 同步到 tm-core storage
    await this.storage.updateTask(taskId, { status: 'blocked' }, this.currentTag);
  }

  /**
   * 检查是否所有任务已完成
   */
  isAllCompleted(): boolean {
    const stats = this.dag.getStats();
    return stats.pending === 0 && stats.running === 0;
  }

  /**
   * 获取统计信息
   */
  getStats() {
    return this.dag.getStats();
  }

  /**
   * 获取单个任务
   */
  getTask(taskId: string): Task | undefined {
    return this.dag.getTask(taskId);
  }

  /**
   * 获取单个任务（异步，从存储读取）
   */
  async getTaskFromStorage(taskId: string): Promise<Task | undefined> {
    const tmCoreTask = await this.storage.loadTask(taskId, this.currentTag);
    return tmCoreTask ? toParallelDevTask(tmCoreTask) : undefined;
  }

  /**
   * 设置调度策略
   */
  setSchedulingStrategy(strategy: SchedulingStrategy): void {
    this.scheduler.setStrategy(strategy);
  }

  // ========== 标签操作 (通过 TagService) ==========

  /**
   * 创建新标签
   */
  async createTag(tagName: string): Promise<void> {
    await this.tagService.createTag(tagName);
  }

  /**
   * 删除标签
   */
  async deleteTag(tagName: string): Promise<void> {
    await this.tagService.deleteTag(tagName);
  }

  /**
   * 复制标签
   */
  async copyTag(sourceTag: string, targetTag: string): Promise<void> {
    await this.tagService.copyTag(sourceTag, targetTag);
  }

  /**
   * 列出所有标签
   */
  async listTags(): Promise<string[]> {
    return this.storage.getAllTags();
  }

  // ========== 高级任务操作 (通过 TaskService) ==========

  /**
   * 获取任务列表（带过滤）
   */
  async getTaskList(options?: {
    withSubtasks?: boolean;
  }): Promise<Task[]> {
    const result = await this.taskService.getTaskList({
      includeSubtasks: options?.withSubtasks ?? false
    });

    return toParallelDevTasks(result.tasks);
  }

  /**
   * 添加新任务
   */
  async addTask(task: Partial<Task>): Promise<Task> {
    const validation = this.validateTask(task);
    if (!validation.valid) {
      throw new Error(`任务验证失败: ${validation.errors.join(', ')}`);
    }

    const tmCoreTask = toTmCoreTask(task as Task);

    // 使用 appendTasks 添加任务
    await this.storage.appendTasks([tmCoreTask], this.currentTag);

    const parallelDevTask = toParallelDevTask(tmCoreTask);

    // 添加到 DAG
    this.dag.addTask(parallelDevTask);

    return parallelDevTask;
  }

  /**
   * 更新任务
   */
  async updateTask(taskId: string, updates: Partial<Task>): Promise<Task> {
    // 转换状态
    const tmCoreUpdates: Record<string, unknown> = { ...updates };
    if (updates.status) {
      tmCoreUpdates.status = toTmCoreStatus(updates.status);
    }

    await this.storage.updateTask(taskId, tmCoreUpdates, this.currentTag);

    // 从存储重新加载
    const updatedTask = await this.storage.loadTask(taskId, this.currentTag);
    if (!updatedTask) {
      throw new Error(`Task ${taskId} not found after update`);
    }

    const parallelDevTask = toParallelDevTask(updatedTask);

    // 更新 DAG 中的任务状态
    const dagTask = this.dag.getTask(taskId);
    if (dagTask && updates.status) {
      if (updates.status === 'completed') {
        this.dag.markCompleted(taskId);
      } else if (updates.status === 'failed') {
        this.dag.markFailed(taskId, updates.error ?? 'Unknown error');
      }
    }

    return parallelDevTask;
  }

  /**
   * 删除任务
   */
  async deleteTask(taskId: string): Promise<void> {
    await this.storage.deleteTask(taskId, this.currentTag);
  }

  // ========== 存储访问 ==========

  /**
   * 获取底层 FileStorage 实例
   */
  getStorage(): FileStorage {
    return this.storage;
  }

  /**
   * 获取 TaskService 实例
   */
  getTaskService(): TaskService {
    return this.taskService;
  }

  /**
   * 获取 TagService 实例
   */
  getTagService(): TagService {
    return this.tagService;
  }

  // ========== AI 功能 ==========

  /**
   * 初始化 AI 服务
   * @param config AI 配置（可选，会从环境变量读取）
   */
  initializeAI(config?: Partial<AIConfig>): void {
    this.taskAIService = new TaskAIService(this.projectRoot, config);
  }

  /**
   * 检查 AI 服务是否可用
   */
  isAIAvailable(): boolean {
    return this.taskAIService?.isAvailable() ?? false;
  }

  /**
   * 获取 TaskAIService 实例
   */
  getTaskAIService(): TaskAIService | null {
    return this.taskAIService;
  }

  /**
   * 解析 PRD 文件生成任务
   * @param prdPath PRD 文件路径
   * @param options 解析选项
   * @returns AI 响应，包含生成的任务
   */
  async parsePRD(
    prdPath: string,
    options: ParsePRDOptions = {}
  ): Promise<AIResponse<Task[]>> {
    if (!this.taskAIService) {
      throw new Error('AI service not initialized. Call initializeAI() first.');
    }

    const response = await this.taskAIService.parsePRD(prdPath, {
      ...options,
      tag: options.tag ?? this.currentTag
    });

    // 重新加载任务到 DAG
    await this.loadTasks(options.tag ?? this.currentTag);

    // 转换为 ParallelDev 任务格式
    const parallelDevTasks = response.result.map((t) =>
      toParallelDevTask({
        id: t.id,
        title: t.title,
        description: t.description,
        status: t.status as 'pending' | 'in-progress' | 'done' | 'blocked' | 'cancelled' | 'deferred' | 'review' | 'completed',
        priority: t.priority as 'high' | 'medium' | 'low',
        dependencies: t.dependencies,
        subtasks: t.subtasks || [],
        details: t.details || '',
        testStrategy: t.testStrategy || '',
        createdAt: t.createdAt,
        updatedAt: t.updatedAt
      })
    );

    return {
      ...response,
      result: parallelDevTasks
    };
  }

  /**
   * 展开任务为子任务
   * @param taskId 任务 ID
   * @param options 展开选项
   * @returns AI 响应，包含展开后的任务
   */
  async expandTask(
    taskId: string,
    options: ExpandTaskOptions = {}
  ): Promise<AIResponse<Task>> {
    if (!this.taskAIService) {
      throw new Error('AI service not initialized. Call initializeAI() first.');
    }

    const response = await this.taskAIService.expandTask(taskId, {
      ...options,
      tag: options.tag ?? this.currentTag
    });

    // 重新加载任务到 DAG
    await this.loadTasks(options.tag ?? this.currentTag);

    // 转换为 ParallelDev 任务格式
    const parallelDevTask = toParallelDevTask({
      id: response.result.id,
      title: response.result.title,
      description: response.result.description,
      status: response.result.status,
      priority: response.result.priority,
      dependencies: response.result.dependencies,
      subtasks: response.result.subtasks || [],
      details: response.result.details || '',
      testStrategy: response.result.testStrategy || '',
      createdAt: response.result.createdAt,
      updatedAt: response.result.updatedAt
    });

    return {
      ...response,
      result: parallelDevTask
    };
  }

  /**
   * 使用 AI 更新任务
   * @param taskId 任务 ID
   * @param prompt 更新指令
   * @returns AI 响应，包含更新后的任务
   */
  async updateTaskWithAI(
    taskId: string,
    prompt: string
  ): Promise<AIResponse<Task>> {
    if (!this.taskAIService) {
      throw new Error('AI service not initialized. Call initializeAI() first.');
    }

    const response = await this.taskAIService.updateTaskWithAI(taskId, prompt, {
      tag: this.currentTag
    });

    // 重新加载任务到 DAG
    await this.loadTasks(this.currentTag);

    // 转换为 ParallelDev 任务格式
    const parallelDevTask = toParallelDevTask({
      id: response.result.id,
      title: response.result.title,
      description: response.result.description,
      status: response.result.status,
      priority: response.result.priority,
      dependencies: response.result.dependencies,
      subtasks: response.result.subtasks || [],
      details: response.result.details || '',
      testStrategy: response.result.testStrategy || '',
      createdAt: response.result.createdAt,
      updatedAt: response.result.updatedAt
    });

    return {
      ...response,
      result: parallelDevTask
    };
  }

  // ========== 任务执行服务 (通过 TaskExecutionService) ==========

  /**
   * 获取 TaskExecutionService 实例
   */
  getTaskExecutionService(): TaskExecutionService {
    return this.taskExecutionService;
  }

  /**
   * 启动任务
   * @param taskId 任务 ID
   * @param options 启动选项
   * @returns 启动结果
   */
  async startTask(
    taskId: string,
    options: StartTaskOptions = {}
  ): Promise<StartTaskResult> {
    return this.taskExecutionService.startTask(taskId, options);
  }

  /**
   * 检查进行中任务冲突
   * @param taskId 目标任务 ID
   * @returns 冲突检查结果
   */
  async checkConflicts(taskId: string): Promise<ConflictCheckResult> {
    return this.taskExecutionService.checkInProgressConflicts(taskId);
  }

  /**
   * 检查任务是否可以启动
   * @param taskId 任务 ID
   * @param force 是否强制（忽略冲突）
   * @returns 是否可以启动
   */
  async canStartTask(taskId: string, force = false): Promise<boolean> {
    return this.taskExecutionService.canStartTask(taskId, force);
  }

  /**
   * 获取下一个可用任务
   * @returns 任务 ID 或 null
   */
  async getNextAvailableTask(): Promise<string | null> {
    return this.taskExecutionService.getNextAvailableTask();
  }
}
