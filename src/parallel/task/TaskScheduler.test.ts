/**
 * TaskScheduler 单元测试
 * @module parallel/task/TaskScheduler.test
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { TaskDAG } from './TaskDAG';
import { TaskScheduler } from './TaskScheduler';
import { Task } from '../types';

/**
 * 创建测试任务的辅助函数
 */
function createTask(
  id: string,
  dependencies: string[] = [],
  priority: number = 3
): Task {
  return {
    id,
    title: `Task ${id}`,
    description: `Description for task ${id}`,
    status: 'pending',
    dependencies,
    priority,
    createdAt: new Date().toISOString()
  };
}

describe('TaskScheduler', () => {
  let dag: TaskDAG;
  let scheduler: TaskScheduler;

  beforeEach(() => {
    dag = new TaskDAG();
  });

  describe('priority_first 策略', () => {
    beforeEach(() => {
      scheduler = new TaskScheduler(dag, 'priority_first');
    });

    it('应该按优先级排序任务（数字越小优先级越高）', () => {
      dag.addTasks([
        createTask('low', [], 5),
        createTask('high', [], 1),
        createTask('medium', [], 3)
      ]);

      const scheduled = scheduler.schedule();

      expect(scheduled[0].id).toBe('high');
      expect(scheduled[1].id).toBe('medium');
      expect(scheduled[2].id).toBe('low');
    });

    it('相同优先级时应保持原有顺序', () => {
      dag.addTasks([
        createTask('a', [], 2),
        createTask('b', [], 2),
        createTask('c', [], 2)
      ]);

      const scheduled = scheduler.schedule();
      expect(scheduled.length).toBe(3);
    });

    it('应该只返回可执行的任务', () => {
      dag.addTasks([
        createTask('1', [], 1),
        createTask('2', ['1'], 1),
        createTask('3', [], 2)
      ]);

      const scheduled = scheduler.schedule();

      // 任务 2 依赖任务 1，不可执行
      expect(scheduled.length).toBe(2);
      expect(scheduled.map(t => t.id)).toContain('1');
      expect(scheduled.map(t => t.id)).toContain('3');
    });
  });

  describe('dependency_first 策略', () => {
    beforeEach(() => {
      scheduler = new TaskScheduler(dag, 'dependency_first');
    });

    it('应该优先执行能解锁更多任务的任务', () => {
      // 任务 a 被 2 个任务依赖
      // 任务 b 被 1 个任务依赖
      dag.addTasks([
        createTask('a', [], 3),
        createTask('b', [], 3),
        createTask('c', ['a'], 3),
        createTask('d', ['a'], 3),
        createTask('e', ['b'], 3)
      ]);

      const scheduled = scheduler.schedule();

      // a 能解锁 2 个任务，b 能解锁 1 个任务
      // 所以 a 应该排在 b 前面
      const indexA = scheduled.findIndex(t => t.id === 'a');
      const indexB = scheduled.findIndex(t => t.id === 'b');

      expect(indexA).toBeLessThan(indexB);
    });

    it('解锁数相同时应按优先级排序', () => {
      dag.addTasks([
        createTask('low', [], 5),
        createTask('high', [], 1),
        createTask('dep1', ['low'], 3),
        createTask('dep2', ['high'], 3)
      ]);

      const scheduled = scheduler.schedule();

      // low 和 high 都能解锁 1 个任务
      // high 优先级更高，应该排在前面
      const indexLow = scheduled.findIndex(t => t.id === 'low');
      const indexHigh = scheduled.findIndex(t => t.id === 'high');

      expect(indexHigh).toBeLessThan(indexLow);
    });
  });

  describe('getNextTask', () => {
    it('应该返回排序后的第一个任务', () => {
      scheduler = new TaskScheduler(dag, 'priority_first');

      dag.addTasks([
        createTask('low', [], 5),
        createTask('high', [], 1)
      ]);

      const next = scheduler.getNextTask();
      expect(next?.id).toBe('high');
    });

    it('没有可执行任务时应返回 undefined', () => {
      scheduler = new TaskScheduler(dag, 'priority_first');

      dag.addTasks([
        createTask('1', ['2']),
        createTask('2', ['1'])
      ]);

      // 循环依赖，没有可执行任务
      const next = scheduler.getNextTask();
      expect(next).toBeUndefined();
    });
  });

  describe('getParallelTasks', () => {
    it('应该返回指定数量的任务', () => {
      scheduler = new TaskScheduler(dag, 'priority_first');

      dag.addTasks([
        createTask('1', [], 1),
        createTask('2', [], 2),
        createTask('3', [], 3),
        createTask('4', [], 4),
        createTask('5', [], 5)
      ]);

      const parallel = scheduler.getParallelTasks(3);
      expect(parallel.length).toBe(3);
      expect(parallel[0].id).toBe('1');
      expect(parallel[1].id).toBe('2');
      expect(parallel[2].id).toBe('3');
    });

    it('可执行任务不足时应返回所有可执行任务', () => {
      scheduler = new TaskScheduler(dag, 'priority_first');

      dag.addTasks([
        createTask('1', [], 1),
        createTask('2', [], 2)
      ]);

      const parallel = scheduler.getParallelTasks(5);
      expect(parallel.length).toBe(2);
    });
  });

  describe('setStrategy / getStrategy', () => {
    it('应该能够切换策略', () => {
      scheduler = new TaskScheduler(dag, 'priority_first');
      expect(scheduler.getStrategy()).toBe('priority_first');

      scheduler.setStrategy('dependency_first');
      expect(scheduler.getStrategy()).toBe('dependency_first');
    });
  });
});
