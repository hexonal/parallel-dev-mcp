/**
 * TaskDAG 单元测试
 * @module parallel/task/TaskDAG.test
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { TaskDAG } from './TaskDAG';
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

describe('TaskDAG', () => {
  let dag: TaskDAG;

  beforeEach(() => {
    dag = new TaskDAG();
  });

  describe('addTask', () => {
    it('应该成功添加任务', () => {
      const task = createTask('1');
      dag.addTask(task);

      const retrieved = dag.getTask('1');
      expect(retrieved).toBeDefined();
      expect(retrieved?.id).toBe('1');
    });

    it('应该拒绝添加重复 ID 的任务', () => {
      dag.addTask(createTask('1'));

      expect(() => dag.addTask(createTask('1'))).toThrow('任务 1 已存在');
    });
  });

  describe('addTasks', () => {
    it('应该批量添加任务', () => {
      const tasks = [createTask('1'), createTask('2'), createTask('3')];
      dag.addTasks(tasks);

      expect(dag.getAllTasks().length).toBe(3);
    });
  });

  describe('getReadyTasks', () => {
    it('应该返回没有依赖的任务', () => {
      dag.addTasks([
        createTask('1'),
        createTask('2'),
        createTask('3', ['1'])
      ]);

      const ready = dag.getReadyTasks();
      expect(ready.length).toBe(2);
      expect(ready.map(t => t.id)).toContain('1');
      expect(ready.map(t => t.id)).toContain('2');
    });

    it('应该在依赖完成后返回任务', () => {
      dag.addTasks([
        createTask('1'),
        createTask('2', ['1'])
      ]);

      // 初始状态只有任务 1 可执行
      let ready = dag.getReadyTasks();
      expect(ready.length).toBe(1);
      expect(ready[0].id).toBe('1');

      // 完成任务 1 后，任务 2 可执行
      dag.markCompleted('1');
      ready = dag.getReadyTasks();
      expect(ready.length).toBe(1);
      expect(ready[0].id).toBe('2');
    });

    it('应该过滤非 pending 状态的任务', () => {
      dag.addTasks([createTask('1'), createTask('2')]);

      dag.markRunning('1', 'worker-1');

      const ready = dag.getReadyTasks();
      expect(ready.length).toBe(1);
      expect(ready[0].id).toBe('2');
    });
  });

  describe('markCompleted', () => {
    it('应该正确标记任务完成', () => {
      dag.addTask(createTask('1'));
      dag.markCompleted('1');

      const task = dag.getTask('1');
      expect(task?.status).toBe('completed');
      expect(task?.completedAt).toBeDefined();
    });

    it('应该拒绝标记不存在的任务', () => {
      expect(() => dag.markCompleted('nonexistent')).toThrow(
        '任务 nonexistent 不存在'
      );
    });
  });

  describe('markFailed', () => {
    it('应该正确标记任务失败', () => {
      dag.addTask(createTask('1'));
      dag.markFailed('1', 'Test error');

      const task = dag.getTask('1');
      expect(task?.status).toBe('failed');
      expect(task?.error).toBe('Test error');
    });
  });

  describe('markRunning', () => {
    it('应该正确标记任务运行中', () => {
      dag.addTask(createTask('1'));
      dag.markRunning('1', 'worker-1');

      const task = dag.getTask('1');
      expect(task?.status).toBe('running');
      expect(task?.assignedWorker).toBe('worker-1');
      expect(task?.startedAt).toBeDefined();
    });
  });

  describe('hasCycle', () => {
    it('无循环依赖时应返回 false', () => {
      dag.addTasks([
        createTask('1'),
        createTask('2', ['1']),
        createTask('3', ['2'])
      ]);

      expect(dag.hasCycle()).toBe(false);
    });

    it('有循环依赖时应返回 true', () => {
      dag.addTasks([
        createTask('a', ['b']),
        createTask('b', ['a'])
      ]);

      expect(dag.hasCycle()).toBe(true);
    });

    it('三个任务循环依赖时应返回 true', () => {
      dag.addTasks([
        createTask('a', ['c']),
        createTask('b', ['a']),
        createTask('c', ['b'])
      ]);

      expect(dag.hasCycle()).toBe(true);
    });
  });

  describe('topologicalSort', () => {
    it('应该正确进行拓扑排序', () => {
      dag.addTasks([
        createTask('1'),
        createTask('2', ['1']),
        createTask('3', ['1']),
        createTask('4', ['2', '3'])
      ]);

      const sorted = dag.topologicalSort();

      // 任务 1 必须在 2, 3 之前
      expect(sorted.indexOf('1')).toBeLessThan(sorted.indexOf('2'));
      expect(sorted.indexOf('1')).toBeLessThan(sorted.indexOf('3'));

      // 任务 2, 3 必须在 4 之前
      expect(sorted.indexOf('2')).toBeLessThan(sorted.indexOf('4'));
      expect(sorted.indexOf('3')).toBeLessThan(sorted.indexOf('4'));
    });

    it('存在循环依赖时应抛出错误', () => {
      dag.addTasks([
        createTask('a', ['b']),
        createTask('b', ['a'])
      ]);

      expect(() => dag.topologicalSort()).toThrow('存在循环依赖');
    });
  });

  describe('getStats', () => {
    it('应该返回正确的统计信息', () => {
      dag.addTasks([
        createTask('1'),
        createTask('2'),
        createTask('3'),
        createTask('4')
      ]);

      dag.markRunning('1', 'worker-1');
      dag.markCompleted('2');
      dag.markFailed('3', 'error');

      const stats = dag.getStats();
      expect(stats.total).toBe(4);
      expect(stats.pending).toBe(1);
      expect(stats.running).toBe(1);
      expect(stats.completed).toBe(1);
      expect(stats.failed).toBe(1);
    });
  });

  describe('clear', () => {
    it('应该清空所有数据', () => {
      dag.addTasks([createTask('1'), createTask('2')]);
      dag.markCompleted('1');

      dag.clear();

      expect(dag.getAllTasks().length).toBe(0);
      expect(dag.getStats().total).toBe(0);
    });
  });
});
