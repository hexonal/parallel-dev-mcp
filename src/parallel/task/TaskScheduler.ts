/**
 * 任务调度器
 * @module parallel/task/TaskScheduler
 *
 * 支持两种调度策略：
 * - priority_first: 高优先级任务优先
 * - dependency_first: 能解锁更多依赖的任务优先
 */

import { Task, SchedulingStrategy } from '../types';
import { TaskDAG } from './TaskDAG';

/**
 * TaskScheduler 负责根据策略对可执行任务进行排序
 */
export class TaskScheduler {
  private strategy: SchedulingStrategy;
  private dag: TaskDAG;

  /**
   * 创建调度器
   * @param dag 任务 DAG
   * @param strategy 调度策略，默认 priority_first
   */
  constructor(dag: TaskDAG, strategy: SchedulingStrategy = 'priority_first') {
    this.dag = dag;
    this.strategy = strategy;
  }

  /**
   * 设置调度策略
   * @param strategy 调度策略
   */
  setStrategy(strategy: SchedulingStrategy): void {
    this.strategy = strategy;
  }

  /**
   * 获取当前调度策略
   * @returns 当前策略
   */
  getStrategy(): SchedulingStrategy {
    return this.strategy;
  }

  /**
   * 调度任务（返回排序后的可执行任务列表）
   * @returns 排序后的任务数组
   */
  schedule(): Task[] {
    const readyTasks = this.dag.getReadyTasks();

    switch (this.strategy) {
      case 'priority_first':
        return this.sortByPriority(readyTasks);
      case 'dependency_first':
        return this.sortByDependencyUnlock(readyTasks);
      default:
        return readyTasks;
    }
  }

  /**
   * 按优先级排序（数字越小优先级越高）
   * @param tasks 任务数组
   * @returns 排序后的任务数组
   */
  private sortByPriority(tasks: Task[]): Task[] {
    return [...tasks].sort((a, b) => a.priority - b.priority);
  }

  /**
   * 按解锁依赖数量排序（能解锁更多任务的优先）
   * @param tasks 任务数组
   * @returns 排序后的任务数组
   */
  private sortByDependencyUnlock(tasks: Task[]): Task[] {
    const allTasks = this.dag.getAllTasks();

    // 计算每个任务被多少其他待执行任务依赖
    const dependentCount = new Map<string, number>();

    for (const task of tasks) {
      let count = 0;

      for (const t of allTasks) {
        const isPending = t.status === 'pending';
        const dependsOnTask = t.dependencies.includes(task.id);

        if (isPending && dependsOnTask) {
          count++;
        }
      }

      dependentCount.set(task.id, count);
    }

    return [...tasks].sort((a, b) => {
      const countA = dependentCount.get(a.id) || 0;
      const countB = dependentCount.get(b.id) || 0;

      // 能解锁更多任务的优先
      if (countB !== countA) {
        return countB - countA;
      }

      // 相同时按优先级排序
      return a.priority - b.priority;
    });
  }

  /**
   * 获取下一个要执行的任务
   * @returns 下一个任务，如果没有则返回 undefined
   */
  getNextTask(): Task | undefined {
    const scheduled = this.schedule();
    return scheduled[0];
  }

  /**
   * 获取可并行执行的任务组
   * @param maxWorkers 最大 Worker 数量
   * @returns 可并行执行的任务数组
   */
  getParallelTasks(maxWorkers: number): Task[] {
    const scheduled = this.schedule();
    return scheduled.slice(0, maxWorkers);
  }
}
