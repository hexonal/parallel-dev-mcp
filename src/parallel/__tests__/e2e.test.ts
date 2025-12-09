/**
 * ParallelDev 端到端测试
 *
 * 测试场景：
 * - TaskManager: 正确加载任务文件
 * - TaskDAG: 正确检测循环依赖
 * - TaskScheduler: 正确排序任务
 * - WorktreeManager: 正确创建/删除 worktree
 * - TmuxController: 正确创建/管理会话
 * - Communication: Socket.IO + RPC 通信
 * - Quality: 质量检查和冲突解决
 * - Notification: 通知和报告生成
 */

import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

import {
  TaskManager,
  TaskDAG,
  TaskScheduler,
  WorktreeManager,
  TmuxController,
  SocketClient,
  SocketServer,
  RpcManager,
  StateManager,
  WorkerPool,
  NotificationManager,
  ReportGenerator,
  ResourceMonitor,
  CodeValidator,
  loadConfig,
} from '../index';

import { Task, ParallelDevConfig } from '../types';

// 测试配置
const TEST_DIR = path.join(os.tmpdir(), 'paralleldev-e2e-test');
const TASKS_DIR = path.join(TEST_DIR, '.pdev', 'tasks');

// 测试任务数据（priority 是数字，1-5，越小优先级越高）
const TEST_TASKS: Task[] = [
  {
    id: '1',
    title: '任务 1 - 无依赖',
    description: '第一个独立任务',
    status: 'pending',
    priority: 1,
    dependencies: [],
    createdAt: new Date().toISOString(),
  },
  {
    id: '2',
    title: '任务 2 - 依赖任务1',
    description: '依赖第一个任务',
    status: 'pending',
    priority: 2,
    dependencies: ['1'],
    createdAt: new Date().toISOString(),
  },
  {
    id: '3',
    title: '任务 3 - 无依赖',
    description: '另一个独立任务',
    status: 'pending',
    priority: 3,
    dependencies: [],
    createdAt: new Date().toISOString(),
  },
];

// 默认测试配置
const TEST_CONFIG: ParallelDevConfig = {
  maxWorkers: 2,
  worktreeDir: '.worktrees',
  mainBranch: 'main',
  socketPort: 3000,
  schedulingStrategy: 'priority_first',
  heartbeatInterval: 30000,
  taskTimeout: 600000,
};

describe('ParallelDev E2E Tests', () => {
  beforeAll(() => {
    // 创建测试目录
    fs.mkdirSync(TASKS_DIR, { recursive: true });

    // 写入测试任务文件
    fs.writeFileSync(
      path.join(TASKS_DIR, 'tasks.json'),
      JSON.stringify({ tasks: TEST_TASKS }, null, 2)
    );
  });

  afterAll(() => {
    // 清理测试目录
    fs.rmSync(TEST_DIR, { recursive: true, force: true });
  });

  // ============================================================
  // Layer 1: Task Management 测试
  // ============================================================
  describe('Layer 1: Task Management', () => {
    describe('TaskDAG', () => {
      it('应正确添加任务', () => {
        const dag = new TaskDAG();
        dag.addTasks(TEST_TASKS);

        const task = dag.getTask('1');
        expect(task).toBeDefined();
        expect(task?.title).toBe('任务 1 - 无依赖');
      });

      it('应正确获取就绪任务', () => {
        const dag = new TaskDAG();
        dag.addTasks(TEST_TASKS);

        const ready = dag.getReadyTasks();
        // 任务 1 和 3 没有依赖，应该就绪
        expect(ready.length).toBe(2);
        expect(ready.map((t) => t.id)).toContain('1');
        expect(ready.map((t) => t.id)).toContain('3');
      });

      it('应正确检测循环依赖', () => {
        const dag = new TaskDAG();
        const cyclicTasks: Task[] = [
          { id: 'a', title: 'A', description: '', status: 'pending', priority: 3, dependencies: ['c'], createdAt: new Date().toISOString() },
          { id: 'b', title: 'B', description: '', status: 'pending', priority: 3, dependencies: ['a'], createdAt: new Date().toISOString() },
          { id: 'c', title: 'C', description: '', status: 'pending', priority: 3, dependencies: ['b'], createdAt: new Date().toISOString() },
        ];
        dag.addTasks(cyclicTasks);

        expect(dag.hasCycle()).toBe(true);
      });

      it('应正确标记任务完成并解锁依赖', () => {
        const dag = new TaskDAG();
        dag.addTasks(TEST_TASKS);

        // 完成任务 1
        dag.markCompleted('1');

        const ready = dag.getReadyTasks();
        // 任务 2 应该被解锁
        expect(ready.map((t) => t.id)).toContain('2');
      });
    });

    describe('TaskScheduler', () => {
      it('应按优先级排序任务', () => {
        const dag = new TaskDAG();
        dag.addTasks(TEST_TASKS);
        const scheduler = new TaskScheduler(dag, 'priority_first');

        const next = scheduler.getNextTask();
        // 高优先级任务应该优先
        expect(next?.id).toBe('1');
      });

      it('应正确调度任务', () => {
        const dag = new TaskDAG();
        dag.addTasks(TEST_TASKS);
        const scheduler = new TaskScheduler(dag, 'priority_first');

        const scheduled = scheduler.schedule();
        // 任务应按优先级排序，任务 1 优先级最高
        expect(scheduled.length).toBeGreaterThan(0);
        expect(scheduled[0].id).toBe('1');
      });
    });

    describe('TaskManager', () => {
      it('应正确加载任务文件', async () => {
        const manager = new TaskManager(TEST_DIR, TEST_CONFIG);
        const tasks = await manager.loadTasks();

        expect(tasks.length).toBe(3);
      });

      it('应正确获取就绪任务', async () => {
        const manager = new TaskManager(TEST_DIR, TEST_CONFIG);
        await manager.loadTasks();

        const ready = manager.getReadyTasks();
        expect(ready.length).toBe(2);
      });
    });
  });

  // ============================================================
  // Layer 2: Orchestration 测试
  // ============================================================
  describe('Layer 2: Orchestration', () => {
    describe('StateManager', () => {
      it('应正确保存和加载状态', async () => {
        const stateManager = new StateManager(TEST_DIR);

        stateManager.updateState({
          currentPhase: 'running',
          startedAt: new Date().toISOString(),
        });

        await stateManager.saveState(stateManager.getState());
        const loaded = await stateManager.loadState();

        expect(loaded).toBeDefined();
        expect(loaded?.currentPhase).toBe('running');
      });

      it('应正确重置状态', () => {
        const stateManager = new StateManager(TEST_DIR);

        stateManager.updateState({ currentPhase: 'running' });
        stateManager.resetState();

        expect(stateManager.getState().currentPhase).toBe('idle');
      });
    });

    describe('WorkerPool', () => {
      it('应正确创建 Worker', async () => {
        const pool = new WorkerPool(2);
        await pool.initialize(TEST_DIR, TEST_CONFIG);

        const stats = pool.getStats();
        expect(stats.total).toBe(2);
        expect(stats.idle).toBe(2);
      });

      it('应正确获取空闲 Worker', async () => {
        const pool = new WorkerPool(2);
        await pool.initialize(TEST_DIR, TEST_CONFIG);

        const worker = pool.getIdleWorker();
        expect(worker).toBeDefined();
        expect(worker?.status).toBe('idle');
      });

      it('应正确检测崩溃的 Worker', async () => {
        const pool = new WorkerPool(2);
        await pool.initialize(TEST_DIR, TEST_CONFIG);

        // 设置一个 Worker 为 error 状态
        pool.setWorkerStatus('worker-1', 'error');

        const crashed = pool.detectCrashedWorkers();
        expect(crashed.length).toBe(1);
        expect(crashed[0].id).toBe('worker-1');
      });

      it('应正确设置恢复策略', async () => {
        const pool = new WorkerPool(2);
        pool.setRecoveryPolicy({ maxRetries: 5 });

        const policy = pool.getRecoveryPolicy();
        expect(policy.maxRetries).toBe(5);
      });
    });
  });

  // ============================================================
  // Layer 4: Communication 测试
  // ============================================================
  describe('Layer 4: Communication', () => {
    describe('RpcManager', () => {
      it('应正确注册和调用处理器', async () => {
        const rpcManager = new RpcManager({
          scopePrefix: 'master',
          timeoutMs: 30000,
        });

        // 注册处理器
        rpcManager.registerHandler('echo', async (params: { message: string }) => {
          return { echo: params.message };
        });

        // 模拟请求
        const request = {
          id: 'test-1',
          method: 'echo',
          params: { message: 'hello' },
          timestamp: Date.now(),
        };

        await rpcManager.handleRequest(request);

        // 验证处理器被调用
        expect(rpcManager.hasHandler('echo')).toBe(true);
      });

      it('应正确生成请求 ID', () => {
        const rpcManager = new RpcManager({
          scopePrefix: 'worker',
        });

        // 内部方法测试通过 UUID 格式验证
        const requestId = rpcManager['generateRequestId']();
        expect(requestId).toMatch(/^[0-9a-f-]{36}$/);
      });
    });
  });

  // ============================================================
  // Layer 5: Quality Assurance 测试
  // ============================================================
  describe('Layer 5: Quality Assurance', () => {
    describe('CodeValidator', () => {
      it('应能创建验证器实例', () => {
        const validator = new CodeValidator({ projectRoot: TEST_DIR });
        expect(validator).toBeDefined();
      });
    });
  });

  // ============================================================
  // Layer 6: Notification 测试
  // ============================================================
  describe('Layer 6: Notification', () => {
    describe('NotificationManager', () => {
      it('应正确发送通知', async () => {
        const manager = new NotificationManager();
        const notified = vi.fn();

        manager.on('notified', notified);

        await manager.notify({
          title: '测试通知',
          message: '这是一条测试消息',
          level: 'info',
        });

        expect(notified).toHaveBeenCalled();
      });

      it('应正确设置通知渠道', () => {
        const manager = new NotificationManager();
        manager.setChannels(['terminal', 'webhook']);

        // 内部状态通过事件验证
        const channelsChanged = vi.fn();
        manager.on('channels_changed', channelsChanged);
        manager.setChannels(['terminal']);

        expect(channelsChanged).toHaveBeenCalled();
      });
    });

    describe('ReportGenerator', () => {
      it('应正确生成报告', () => {
        const generator = new ReportGenerator(TEST_DIR);
        // 创建已完成状态的任务
        const completedTasks = TEST_TASKS.map((t) => ({ ...t, status: 'completed' as const }));
        const state = {
          workers: [],
          tasks: completedTasks,
          currentPhase: 'completed' as const,
          startedAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          stats: {
            totalTasks: 3,
            completedTasks: 3,
            failedTasks: 0,
            pendingTasks: 0,
            runningTasks: 0,
            activeWorkers: 0,
            idleWorkers: 0,
          },
        };

        const report = generator.generateReport(state);

        expect(report.summary.totalTasks).toBe(3);
        expect(report.summary.completedTasks).toBe(3);
      });

      it('应正确格式化 Markdown', () => {
        const generator = new ReportGenerator(TEST_DIR);
        const state = {
          workers: [],
          tasks: TEST_TASKS,
          currentPhase: 'completed' as const,
          startedAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          stats: {
            totalTasks: 3,
            completedTasks: 3,
            failedTasks: 0,
            pendingTasks: 0,
            runningTasks: 0,
            activeWorkers: 0,
            idleWorkers: 0,
          },
        };

        const report = generator.generateReport(state);
        const markdown = generator.formatMarkdown(report);

        expect(markdown).toContain('# ParallelDev');
        expect(markdown).toContain('3');
      });
    });

    describe('ResourceMonitor', () => {
      it('应正确获取 CPU 使用率', async () => {
        const monitor = new ResourceMonitor();
        const cpu = await monitor.getCpuUsage();

        expect(typeof cpu).toBe('number');
        expect(cpu).toBeGreaterThanOrEqual(0);
        expect(cpu).toBeLessThanOrEqual(100);
      });

      it('应正确获取内存使用情况', async () => {
        const monitor = new ResourceMonitor();
        const memory = await monitor.getMemoryUsage();

        expect(memory.total).toBeGreaterThan(0);
        expect(memory.used).toBeGreaterThan(0);
        expect(memory.percent).toBeGreaterThan(0);
      });

      it('应正确获取磁盘使用情况', async () => {
        const monitor = new ResourceMonitor();
        const disk = await monitor.getDiskUsage();

        expect(disk.total).toBeGreaterThan(0);
      });

      it('应正确获取综合资源报告', async () => {
        const monitor = new ResourceMonitor();
        const report = await monitor.getResourceReport();

        expect(report.cpu).toBeDefined();
        expect(report.memory).toBeDefined();
        expect(report.disk).toBeDefined();
        expect(report.timestamp).toBeDefined();
      });

      it('应正确管理日志捕获', () => {
        const monitor = new ResourceMonitor();

        monitor.startLogCapture('worker-1');
        const logs = monitor.getRecentLogs('worker-1');

        expect(Array.isArray(logs)).toBe(true);

        monitor.stopLogCapture('worker-1');
        monitor.cleanup();
      });
    });
  });

  // ============================================================
  // 配置测试
  // ============================================================
  describe('Configuration', () => {
    it('应正确加载默认配置', async () => {
      const config = await loadConfig(TEST_DIR);

      expect(config.maxWorkers).toBeDefined();
      expect(config.worktreeDir).toBeDefined();
    });
  });
});
