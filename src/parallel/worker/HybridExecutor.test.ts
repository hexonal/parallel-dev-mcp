/**
 * HybridExecutor 单元测试
 * @module parallel/worker/HybridExecutor.test
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { HybridExecutor, HybridExecutorConfig } from './HybridExecutor';
import { TmuxController } from '../tmux/TmuxController';
import { SessionMonitor } from '../tmux/SessionMonitor';
import { Task } from '../types';

/**
 * 创建测试任务
 */
function createTestTask(id: string = 'test-001'): Task {
  return {
    id,
    title: 'Test Task',
    description: 'This is a test task for unit testing',
    status: 'pending',
    dependencies: [],
    priority: 2,
    createdAt: new Date().toISOString(),
    estimatedHours: 1,
    tags: ['test', 'unit']
  };
}

/**
 * 创建 Mock TmuxController
 */
function createMockTmuxController() {
  return {
    sendCommand: vi.fn().mockResolvedValue(undefined),
    captureOutput: vi.fn().mockResolvedValue(''),
    sendInterrupt: vi.fn().mockResolvedValue(undefined),
    sessionExists: vi.fn().mockReturnValue(true),
    createSession: vi.fn().mockResolvedValue('test-session'),
    killSession: vi.fn().mockResolvedValue(undefined),
    getSessionName: vi.fn().mockImplementation((id: string) => `pdev-${id}`),
    sendKeys: vi.fn().mockResolvedValue(undefined)
  } as unknown as TmuxController;
}

/**
 * 创建 Mock SessionMonitor
 */
function createMockSessionMonitor() {
  return {
    startMonitoring: vi.fn(),
    stopMonitoring: vi.fn(),
    stopAll: vi.fn(),
    getMonitoredSessions: vi.fn().mockReturnValue([]),
    isMonitoring: vi.fn().mockReturnValue(false),
    setCheckInterval: vi.fn()
  } as unknown as SessionMonitor;
}

describe('HybridExecutor', () => {
  let executor: HybridExecutor;
  let mockTmux: TmuxController;
  let mockMonitor: SessionMonitor;
  const testSession = 'test-worker-session';
  const testWorktreePath = '/tmp/test-worktree';

  beforeEach(() => {
    vi.clearAllMocks();
    mockTmux = createMockTmuxController();
    mockMonitor = createMockSessionMonitor();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('constructor', () => {
    it('应该使用默认配置创建实例', () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession);

      const config = executor.getConfig();
      expect(config.timeout).toBe(600000);
      expect(config.permissionMode).toBe('acceptEdits');
      expect(config.monitorInterval).toBe(2000);
      expect(config.maxTurns).toBe(50);
      expect(config.enableHooks).toBe(true);
    });

    it('应该合并自定义配置', () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession, {
        timeout: 300000,
        permissionMode: 'bypassPermissions',
        model: 'claude-3-opus'
      });

      const config = executor.getConfig();
      expect(config.timeout).toBe(300000);
      expect(config.permissionMode).toBe('bypassPermissions');
      expect(config.model).toBe('claude-3-opus');
      // 未指定的应该使用默认值
      expect(config.monitorInterval).toBe(2000);
    });
  });

  describe('execute - fire-and-forget 模式', () => {
    beforeEach(() => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession, {
        timeout: 5000
      });
    });

    it('fire-and-forget 模式应该立即返回', async () => {
      const task = createTestTask();

      const result = await executor.execute(task, testWorktreePath, true);

      expect(result.success).toBe(true);
      expect(result.output).toBe('Task started in background');
      expect(result.metadata?.mode).toBe('fire-and-forget');
      expect(result.metadata?.executor).toBe('hybrid-tmux');
    });
  });

  describe('配置方法', () => {
    beforeEach(() => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession);
    });

    it('setTimeout 应该更新超时配置', () => {
      executor.setTimeout(30000);
      expect(executor.getConfig().timeout).toBe(30000);
    });

    it('updateConfig 应该合并配置', () => {
      executor.updateConfig({
        permissionMode: 'bypassPermissions',
        monitorInterval: 1000
      });

      const config = executor.getConfig();
      expect(config.permissionMode).toBe('bypassPermissions');
      expect(config.monitorInterval).toBe(1000);
      // 其他配置应保持不变
      expect(config.timeout).toBe(600000);
    });

    it('getConfig 应该返回配置副本', () => {
      const config1 = executor.getConfig();
      const config2 = executor.getConfig();

      expect(config1).not.toBe(config2);
      expect(config1).toEqual(config2);
    });
  });

  describe('getSessionOutput', () => {
    it('会话未启动时应返回 null', async () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession);

      const output = await executor.getSessionOutput();
      expect(output).toBeNull();
    });
  });
});
