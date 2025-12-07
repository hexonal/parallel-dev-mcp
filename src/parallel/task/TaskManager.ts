/**
 * 任务管理器（原 TaskMasterAdapter）
 * @module parallel/task/TaskManager
 *
 * 负责加载、验证、保存任务文件
 * 集成 TaskDAG 和 TaskScheduler
 */

import * as fs from 'fs';
import * as path from 'path';
import { Task, TasksFileSchema, SchedulingStrategy, ParallelDevConfig } from '../types';
import { TaskDAG } from './TaskDAG';
import { TaskScheduler } from './TaskScheduler';

/**
 * TaskManager 整合任务文件管理、DAG、调度器
 */
export class TaskManager {
  private projectRoot: string;
  private tasksFilePath: string;
  private dag: TaskDAG;
  private scheduler: TaskScheduler;

  /**
   * 创建任务管理器
   * @param projectRoot 项目根目录
   * @param config 配置对象
   */
  constructor(projectRoot: string, config: ParallelDevConfig) {
    this.projectRoot = projectRoot;
    this.tasksFilePath = path.join(
      projectRoot,
      '.taskmaster/tasks/tasks.json'
    );
    this.dag = new TaskDAG();
    this.scheduler = new TaskScheduler(this.dag, config.schedulingStrategy);
  }

  /**
   * 检查任务文件是否存在
   * @returns 是否存在
   */
  tasksFileExists(): boolean {
    return fs.existsSync(this.tasksFilePath);
  }

  /**
   * 加载任务文件
   * @returns 任务数组
   * @throws Error 如果文件不存在或格式错误
   */
  async loadTasks(): Promise<Task[]> {
    if (!this.tasksFileExists()) {
      throw new Error(`任务文件不存在: ${this.tasksFilePath}`);
    }

    const content = fs.readFileSync(this.tasksFilePath, 'utf-8');
    const data = JSON.parse(content);

    // Zod 运行时验证
    const result = TasksFileSchema.safeParse(data);
    if (!result.success) {
      throw new Error(`任务文件格式错误: ${result.error.message}`);
    }

    // 重新初始化 DAG
    this.dag = new TaskDAG();
    this.dag.addTasks(result.data.tasks as Task[]);

    // 更新调度器的 DAG 引用
    this.scheduler = new TaskScheduler(
      this.dag,
      this.scheduler.getStrategy()
    );

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
    const data = {
      tasks,
      meta: {
        generatedAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
    };

    // 确保目录存在
    const dir = path.dirname(this.tasksFilePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    fs.writeFileSync(this.tasksFilePath, JSON.stringify(data, null, 2));
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
   * @returns TaskDAG 实例
   */
  getDAG(): TaskDAG {
    return this.dag;
  }

  /**
   * 获取调度器实例
   * @returns TaskScheduler 实例
   */
  getScheduler(): TaskScheduler {
    return this.scheduler;
  }

  /**
   * 获取可执行任务
   * @returns 可执行任务数组
   */
  getReadyTasks(): Task[] {
    return this.dag.getReadyTasks();
  }

  /**
   * 调度下一批任务
   * @param maxWorkers 最大 Worker 数量
   * @returns 下一批可执行任务
   */
  scheduleNextBatch(maxWorkers: number): Task[] {
    return this.scheduler.getParallelTasks(maxWorkers);
  }

  /**
   * 标记任务开始执行
   * @param taskId 任务 ID
   * @param workerId Worker ID
   */
  markTaskStarted(taskId: string, workerId: string): void {
    this.dag.markRunning(taskId, workerId);
  }

  /**
   * 标记任务完成
   * @param taskId 任务 ID
   */
  markTaskCompleted(taskId: string): void {
    this.dag.markCompleted(taskId);
  }

  /**
   * 标记任务失败
   * @param taskId 任务 ID
   * @param error 错误信息
   */
  markTaskFailed(taskId: string, error: string): void {
    this.dag.markFailed(taskId, error);
  }

  /**
   * 检查是否所有任务已完成
   * @returns 是否全部完成
   */
  isAllCompleted(): boolean {
    const stats = this.dag.getStats();
    return stats.pending === 0 && stats.running === 0;
  }

  /**
   * 获取统计信息
   * @returns 任务统计
   */
  getStats() {
    return this.dag.getStats();
  }

  /**
   * 获取单个任务
   * @param taskId 任务 ID
   * @returns 任务对象或 undefined
   */
  getTask(taskId: string): Task | undefined {
    return this.dag.getTask(taskId);
  }

  /**
   * 设置调度策略
   * @param strategy 调度策略
   */
  setSchedulingStrategy(strategy: SchedulingStrategy): void {
    this.scheduler.setStrategy(strategy);
  }
}
