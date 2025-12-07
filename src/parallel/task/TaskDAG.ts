/**
 * 任务依赖有向无环图
 * @module parallel/task/TaskDAG
 */

import { Task, TaskStatus } from '../types';

/**
 * TaskDAG 管理任务之间的依赖关系
 * 提供依赖检查、循环检测、拓扑排序等功能
 */
export class TaskDAG {
  private tasks: Map<string, Task> = new Map();
  private completedTasks: Set<string> = new Set();
  private failedTasks: Set<string> = new Set();

  /**
   * 添加任务到 DAG
   * @param task 任务对象
   * @throws Error 如果任务 ID 已存在
   */
  addTask(task: Task): void {
    if (this.tasks.has(task.id)) {
      throw new Error(`任务 ${task.id} 已存在`);
    }
    this.tasks.set(task.id, { ...task });
  }

  /**
   * 批量添加任务
   * @param tasks 任务数组
   */
  addTasks(tasks: Task[]): void {
    for (const task of tasks) {
      this.addTask(task);
    }
  }

  /**
   * 获取可执行任务（依赖已满足且状态为 pending）
   * @returns 可执行任务数组
   */
  getReadyTasks(): Task[] {
    const ready: Task[] = [];

    for (const task of this.tasks.values()) {
      if (task.status !== 'pending') {
        continue;
      }

      const dependenciesMet = task.dependencies.every(
        depId => this.completedTasks.has(depId)
      );

      if (dependenciesMet) {
        ready.push({ ...task });
      }
    }

    return ready;
  }

  /**
   * 标记任务为完成
   * @param taskId 任务 ID
   * @throws Error 如果任务不存在
   */
  markCompleted(taskId: string): void {
    const task = this.tasks.get(taskId);
    if (!task) {
      throw new Error(`任务 ${taskId} 不存在`);
    }

    task.status = 'completed';
    task.completedAt = new Date().toISOString();
    this.completedTasks.add(taskId);
  }

  /**
   * 标记任务为失败
   * @param taskId 任务 ID
   * @param error 错误信息
   * @throws Error 如果任务不存在
   */
  markFailed(taskId: string, error: string): void {
    const task = this.tasks.get(taskId);
    if (!task) {
      throw new Error(`任务 ${taskId} 不存在`);
    }

    task.status = 'failed';
    task.error = error;
    this.failedTasks.add(taskId);
  }

  /**
   * 标记任务为进行中
   * @param taskId 任务 ID
   * @param workerId 分配的 Worker ID
   * @throws Error 如果任务不存在
   */
  markRunning(taskId: string, workerId: string): void {
    const task = this.tasks.get(taskId);
    if (!task) {
      throw new Error(`任务 ${taskId} 不存在`);
    }

    task.status = 'running';
    task.assignedWorker = workerId;
    task.startedAt = new Date().toISOString();
  }

  /**
   * 检测是否存在循环依赖
   * @returns true 如果存在循环
   */
  hasCycle(): boolean {
    const visited = new Set<string>();
    const recStack = new Set<string>();

    const dfs = (taskId: string): boolean => {
      visited.add(taskId);
      recStack.add(taskId);

      const task = this.tasks.get(taskId);
      if (!task) {
        return false;
      }

      for (const depId of task.dependencies) {
        if (!visited.has(depId)) {
          if (dfs(depId)) {
            return true;
          }
        } else if (recStack.has(depId)) {
          return true;
        }
      }

      recStack.delete(taskId);
      return false;
    };

    for (const taskId of this.tasks.keys()) {
      if (!visited.has(taskId)) {
        if (dfs(taskId)) {
          return true;
        }
      }
    }

    return false;
  }

  /**
   * 拓扑排序
   * @returns 排序后的任务 ID 数组
   * @throws Error 如果存在循环依赖
   */
  topologicalSort(): string[] {
    if (this.hasCycle()) {
      throw new Error('存在循环依赖，无法拓扑排序');
    }

    const result: string[] = [];
    const visited = new Set<string>();

    const visit = (taskId: string) => {
      if (visited.has(taskId)) {
        return;
      }
      visited.add(taskId);

      const task = this.tasks.get(taskId);
      if (!task) {
        return;
      }

      for (const depId of task.dependencies) {
        visit(depId);
      }

      result.push(taskId);
    };

    for (const taskId of this.tasks.keys()) {
      visit(taskId);
    }

    return result;
  }

  /**
   * 获取任务
   * @param taskId 任务 ID
   * @returns 任务对象（副本）或 undefined
   */
  getTask(taskId: string): Task | undefined {
    const task = this.tasks.get(taskId);
    return task ? { ...task } : undefined;
  }

  /**
   * 获取所有任务
   * @returns 所有任务数组（副本）
   */
  getAllTasks(): Task[] {
    return Array.from(this.tasks.values()).map(t => ({ ...t }));
  }

  /**
   * 获取统计信息
   * @returns 任务统计
   */
  getStats(): {
    total: number;
    pending: number;
    running: number;
    completed: number;
    failed: number;
  } {
    let pending = 0;
    let running = 0;
    let completed = 0;
    let failed = 0;

    for (const task of this.tasks.values()) {
      switch (task.status) {
        case 'pending':
          pending++;
          break;
        case 'running':
          running++;
          break;
        case 'completed':
          completed++;
          break;
        case 'failed':
          failed++;
          break;
      }
    }

    return {
      total: this.tasks.size,
      pending,
      running,
      completed,
      failed
    };
  }

  /**
   * 清空 DAG
   */
  clear(): void {
    this.tasks.clear();
    this.completedTasks.clear();
    this.failedTasks.clear();
  }
}
