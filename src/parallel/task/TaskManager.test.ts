/**
 * TaskManager 单元测试
 * @module parallel/task/TaskManager.test
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import { TaskManager } from './TaskManager';
import { DEFAULT_CONFIG } from '../config';
import { Task } from '../types';

// 测试目录
const TEST_DIR = path.join(__dirname, '../../../test-temp');
const TASKS_DIR = path.join(TEST_DIR, '.taskmaster/tasks');
const TASKS_FILE = path.join(TASKS_DIR, 'tasks.json');

/**
 * 创建测试任务文件
 */
function createTasksFile(tasks: Partial<Task>[]): void {
  const fullTasks = tasks.map((t, i) => ({
    id: t.id || String(i + 1),
    title: t.title || `Task ${i + 1}`,
    description: t.description || '',
    status: t.status || 'pending',
    dependencies: t.dependencies || [],
    priority: t.priority || 'medium',
    createdAt: new Date().toISOString()
  }));

  const data = {
    tasks: fullTasks,
    metadata: {
      version: '1.0.0',
      lastModified: new Date().toISOString(),
      taskCount: fullTasks.length,
      completedCount: 0,
      tags: ['master']
    }
  };

  fs.mkdirSync(TASKS_DIR, { recursive: true });
  fs.writeFileSync(TASKS_FILE, JSON.stringify(data, null, 2));
}

/**
 * 清理测试目录
 */
function cleanup(): void {
  if (fs.existsSync(TEST_DIR)) {
    fs.rmSync(TEST_DIR, { recursive: true });
  }
}

describe('TaskManager', () => {
  beforeEach(() => {
    cleanup();
    fs.mkdirSync(TEST_DIR, { recursive: true });
  });

  afterEach(() => {
    cleanup();
  });

  describe('tasksFileExists', () => {
    it('文件不存在时应返回 false', async () => {
      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);
      expect(await manager.tasksFileExists()).toBe(false);
    });

    it('文件存在时应返回 true', async () => {
      createTasksFile([{ id: '1', title: 'Test' }]);

      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);
      expect(await manager.tasksFileExists()).toBe(true);
    });
  });

  describe('loadTasks', () => {
    it('应该正确加载任务文件', async () => {
      createTasksFile([
        { id: '1', title: 'Task 1' },
        { id: '2', title: 'Task 2', dependencies: ['1'] }
      ]);

      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);
      const tasks = await manager.loadTasks();

      expect(tasks.length).toBe(2);
      expect(tasks[0].id).toBe('1');
      expect(tasks[1].dependencies).toContain('1');
    });

    it('文件不存在时应返回空数组', async () => {
      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);
      const tasks = await manager.loadTasks();
      expect(tasks).toEqual([]);
    });

    it('存在循环依赖时应抛出错误', async () => {
      createTasksFile([
        { id: 'a', dependencies: ['b'] },
        { id: 'b', dependencies: ['a'] }
      ]);

      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);

      await expect(manager.loadTasks()).rejects.toThrow('循环依赖');
    });
  });

  describe('saveTasks', () => {
    it('应该保存任务状态到文件', async () => {
      createTasksFile([{ id: '1', title: 'Test' }]);

      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);
      await manager.loadTasks();

      await manager.markTaskCompleted('1');
      await manager.saveTasks();

      // 重新读取验证
      const content = fs.readFileSync(TASKS_FILE, 'utf-8');
      const data = JSON.parse(content);

      expect(data.tasks[0].status).toBe('done');
    });
  });

  describe('validateTask', () => {
    it('有效任务应通过验证', () => {
      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);

      const result = manager.validateTask({
        id: '1',
        title: 'Valid Task',
        priority: 3
      });

      expect(result.valid).toBe(true);
      expect(result.errors.length).toBe(0);
    });

    it('空 ID 应不通过验证', () => {
      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);

      const result = manager.validateTask({
        id: '',
        title: 'Test'
      });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('任务 ID 不能为空');
    });

    it('空标题应不通过验证', () => {
      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);

      const result = manager.validateTask({
        id: '1',
        title: ''
      });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('任务标题不能为空');
    });

    it('无效优先级应不通过验证', () => {
      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);

      const result = manager.validateTask({
        id: '1',
        title: 'Test',
        priority: 10
      });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('优先级必须在 1-5 之间');
    });
  });

  describe('getReadyTasks', () => {
    it('应该返回可执行任务', async () => {
      createTasksFile([
        { id: '1' },
        { id: '2', dependencies: ['1'] }
      ]);

      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);
      await manager.loadTasks();

      const ready = manager.getReadyTasks();
      expect(ready.length).toBe(1);
      expect(ready[0].id).toBe('1');
    });
  });

  describe('scheduleNextBatch', () => {
    it('应该返回指定数量的任务', async () => {
      createTasksFile([
        { id: '1', priority: 1 },
        { id: '2', priority: 2 },
        { id: '3', priority: 3 }
      ]);

      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);
      await manager.loadTasks();

      const batch = manager.scheduleNextBatch(2);
      expect(batch.length).toBe(2);
    });
  });

  describe('任务状态管理', () => {
    it('应该正确标记任务状态', async () => {
      createTasksFile([{ id: '1' }, { id: '2' }]);

      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);
      await manager.loadTasks();

      manager.markTaskStarted('1', 'worker-1');
      expect(manager.getTask('1')?.status).toBe('running');
      expect(manager.getTask('1')?.assignedWorker).toBe('worker-1');

      await manager.markTaskCompleted('1');
      expect(manager.getTask('1')?.status).toBe('completed');

      await manager.markTaskFailed('2', 'Test error');
      expect(manager.getTask('2')?.status).toBe('failed');
      expect(manager.getTask('2')?.error).toBe('Test error');
    });
  });

  describe('isAllCompleted', () => {
    it('所有任务完成时应返回 true', async () => {
      createTasksFile([{ id: '1' }, { id: '2' }]);

      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);
      await manager.loadTasks();

      await manager.markTaskCompleted('1');
      await manager.markTaskCompleted('2');

      expect(manager.isAllCompleted()).toBe(true);
    });

    it('有任务未完成时应返回 false', async () => {
      createTasksFile([{ id: '1' }, { id: '2' }]);

      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);
      await manager.loadTasks();

      await manager.markTaskCompleted('1');

      expect(manager.isAllCompleted()).toBe(false);
    });
  });

  describe('getStats', () => {
    it('应该返回正确的统计信息', async () => {
      createTasksFile([
        { id: '1' },
        { id: '2' },
        { id: '3' },
        { id: '4' }
      ]);

      const manager = new TaskManager(TEST_DIR, DEFAULT_CONFIG);
      await manager.loadTasks();

      manager.markTaskStarted('1', 'w1');
      await manager.markTaskCompleted('2');
      await manager.markTaskFailed('3', 'err');

      const stats = manager.getStats();
      expect(stats.total).toBe(4);
      expect(stats.running).toBe(1);
      expect(stats.completed).toBe(1);
      expect(stats.failed).toBe(1);
      expect(stats.pending).toBe(1);
    });
  });
});
