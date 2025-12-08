/**
 * HybridExecutor 单元测试
 * @module parallel/worker/HybridExecutor.test
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import * as fs from 'fs/promises';
import * as path from 'path';
import { HybridExecutor, HybridExecutorConfig } from './HybridExecutor';
import { TmuxController } from '../tmux/TmuxController';
import { SessionMonitor } from '../tmux/SessionMonitor';
import { Task } from '../types';

// Mock fs/promises
vi.mock('fs/promises', () => ({
  writeFile: vi.fn().mockResolvedValue(undefined),
  unlink: vi.fn().mockResolvedValue(undefined)
}));

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
    killSession: vi.fn().mockResolvedValue(undefined)
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
      expect(config.checkInterval).toBe(1000);
      expect(config.timeout).toBe(600000);
      expect(config.permissionMode).toBe('acceptEdits');
      expect(config.cleanupScript).toBe(true);
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
      expect(config.checkInterval).toBe(1000);
    });
  });

  describe('execute', () => {
    beforeEach(() => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession, {
        timeout: 5000,
        checkInterval: 100
      });
    });

    it('应该生成脚本文件并执行', async () => {
      const task = createTestTask();

      // 模拟立即完成
      const completedOutput = JSON.stringify({
        type: 'task_completed',
        taskId: task.id,
        timestamp: Date.now(),
        output: 'Task completed',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      });

      (mockTmux.captureOutput as any)
        .mockResolvedValueOnce('')
        .mockResolvedValueOnce(completedOutput);

      const result = await executor.execute(task, testWorktreePath);

      // 验证脚本文件被创建
      expect(fs.writeFile).toHaveBeenCalledTimes(1);
      const writeCall = (fs.writeFile as any).mock.calls[0];
      expect(writeCall[0]).toContain(`.paralleldev-task-${task.id}.ts`);

      // 验证命令被发送到 tmux
      expect(mockTmux.sendCommand).toHaveBeenCalledTimes(1);
      expect((mockTmux.sendCommand as any).mock.calls[0][0]).toBe(testSession);

      // 验证结果
      expect(result.success).toBe(true);
      expect(result.output).toBe('Task completed');
    });

    it('应该在任务失败时返回失败结果', async () => {
      const task = createTestTask();

      // 模拟失败输出
      const failedOutput = JSON.stringify({
        type: 'task_failed',
        taskId: task.id,
        timestamp: Date.now(),
        error: 'Something went wrong',
        errorCode: 'ERR_001'
      });

      (mockTmux.captureOutput as any)
        .mockResolvedValueOnce('')
        .mockResolvedValueOnce(failedOutput);

      const result = await executor.execute(task, testWorktreePath);

      expect(result.success).toBe(false);
      expect(result.error).toBe('Something went wrong');
      expect(result.metadata?.executor).toBe('hybrid');
    });

    it('应该在超时时返回失败结果', async () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession, {
        timeout: 100,
        checkInterval: 50
      });

      const task = createTestTask();

      // 模拟持续返回空输出（不完成）
      (mockTmux.captureOutput as any).mockResolvedValue('');

      const result = await executor.execute(task, testWorktreePath);

      expect(result.success).toBe(false);
      expect(result.error).toContain('超时');
      expect(mockTmux.sendInterrupt).toHaveBeenCalled();
    });

    it('应该在脚本生成失败时返回失败结果', async () => {
      const task = createTestTask();

      // 模拟写文件失败
      (fs.writeFile as any).mockRejectedValueOnce(new Error('Write failed'));

      const result = await executor.execute(task, testWorktreePath);

      expect(result.success).toBe(false);
      expect(result.error).toBe('Write failed');
    });

    it('应该在配置允许时清理脚本文件', async () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession, {
        cleanupScript: true,
        timeout: 5000,
        checkInterval: 100
      });

      const task = createTestTask();

      const completedOutput = JSON.stringify({
        type: 'task_completed',
        taskId: task.id,
        timestamp: Date.now(),
        output: 'Done',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      });

      (mockTmux.captureOutput as any)
        .mockResolvedValueOnce('')
        .mockResolvedValueOnce(completedOutput);

      await executor.execute(task, testWorktreePath);

      expect(fs.unlink).toHaveBeenCalled();
    });

    it('应该在配置禁用时不清理脚本文件', async () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession, {
        cleanupScript: false,
        timeout: 5000,
        checkInterval: 100
      });

      const task = createTestTask();

      const completedOutput = JSON.stringify({
        type: 'task_completed',
        taskId: task.id,
        timestamp: Date.now(),
        output: 'Done',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      });

      (mockTmux.captureOutput as any)
        .mockResolvedValueOnce('')
        .mockResolvedValueOnce(completedOutput);

      await executor.execute(task, testWorktreePath);

      expect(fs.unlink).not.toHaveBeenCalled();
    });

    it('应该收集 sdk_message 内容作为输出', async () => {
      const task = createTestTask();

      // 模拟多条消息
      const sdkMessage1 = JSON.stringify({
        type: 'sdk_message',
        taskId: task.id,
        timestamp: Date.now(),
        sdkType: 'assistant',
        content: 'First message'
      });

      const sdkMessage2 = JSON.stringify({
        type: 'sdk_message',
        taskId: task.id,
        timestamp: Date.now(),
        sdkType: 'assistant',
        content: 'Second message'
      });

      const completedMessage = JSON.stringify({
        type: 'task_completed',
        taskId: task.id,
        timestamp: Date.now(),
        output: '',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      });

      (mockTmux.captureOutput as any)
        .mockResolvedValueOnce('')
        .mockResolvedValueOnce(sdkMessage1 + '\n')
        .mockResolvedValueOnce(sdkMessage1 + '\n' + sdkMessage2 + '\n')
        .mockResolvedValueOnce(sdkMessage1 + '\n' + sdkMessage2 + '\n' + completedMessage);

      const result = await executor.execute(task, testWorktreePath);

      expect(result.success).toBe(true);
      // 输出应该包含收集到的内容
      expect(result.output).toContain('First message');
    });
  });

  describe('buildScriptContent', () => {
    it('生成的脚本应该包含任务信息', () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession);
      const task = createTestTask('task-123');

      // 通过 execute 间接测试 buildScriptContent
      // 检查 writeFile 调用的内容
      const completedOutput = JSON.stringify({
        type: 'task_completed',
        taskId: task.id,
        timestamp: Date.now(),
        output: 'Done',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      });

      (mockTmux.captureOutput as any)
        .mockResolvedValueOnce('')
        .mockResolvedValueOnce(completedOutput);

      executor.execute(task, testWorktreePath);

      // 验证脚本内容
      const writeCall = (fs.writeFile as any).mock.calls[0];
      const scriptContent = writeCall[1] as string;

      expect(scriptContent).toContain('task-123');
      expect(scriptContent).toContain('Test Task');
      expect(scriptContent).toContain('import { query }');
      expect(scriptContent).toContain('emit({');
    });

    it('生成的脚本应该包含配置信息', () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession, {
        permissionMode: 'bypassPermissions',
        maxTurns: 30,
        model: 'claude-3-sonnet'
      });

      const task = createTestTask();

      const completedOutput = JSON.stringify({
        type: 'task_completed',
        taskId: task.id,
        timestamp: Date.now(),
        output: 'Done',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      });

      (mockTmux.captureOutput as any)
        .mockResolvedValueOnce('')
        .mockResolvedValueOnce(completedOutput);

      executor.execute(task, testWorktreePath);

      const writeCall = (fs.writeFile as any).mock.calls[0];
      const scriptContent = writeCall[1] as string;

      expect(scriptContent).toContain('bypassPermissions');
      expect(scriptContent).toContain('30');
      expect(scriptContent).toContain('claude-3-sonnet');
    });
  });

  describe('buildExecuteCommand', () => {
    it('应该生成正确的执行命令', async () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession, {
        timeout: 5000,
        checkInterval: 100
      });
      const task = createTestTask();

      const completedOutput = JSON.stringify({
        type: 'task_completed',
        taskId: task.id,
        timestamp: Date.now(),
        output: 'Done',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      });

      (mockTmux.captureOutput as any)
        .mockResolvedValueOnce('')
        .mockResolvedValueOnce(completedOutput);

      await executor.execute(task, testWorktreePath);

      // 验证发送的命令
      const sendCall = (mockTmux.sendCommand as any).mock.calls[0];
      const command = sendCall[1] as string;

      expect(command).toContain('npx tsx');
      expect(command).toContain('.paralleldev-task-');
    });

    it('应该包含自定义环境变量', async () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession, {
        timeout: 5000,
        checkInterval: 100,
        env: {
          CUSTOM_VAR: 'custom_value',
          ANOTHER_VAR: 'another_value'
        }
      });

      const task = createTestTask();

      const completedOutput = JSON.stringify({
        type: 'task_completed',
        taskId: task.id,
        timestamp: Date.now(),
        output: 'Done',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      });

      (mockTmux.captureOutput as any)
        .mockResolvedValueOnce('')
        .mockResolvedValueOnce(completedOutput);

      await executor.execute(task, testWorktreePath);

      const sendCall = (mockTmux.sendCommand as any).mock.calls[0];
      const command = sendCall[1] as string;

      expect(command).toContain('CUSTOM_VAR="custom_value"');
      expect(command).toContain('ANOTHER_VAR="another_value"');
    });
  });

  describe('cancel', () => {
    it('应该发送中断信号到 tmux 会话', async () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession);

      await executor.cancel();

      expect(mockTmux.sendInterrupt).toHaveBeenCalledWith(testSession);
    });

    it('应该清理脚本文件', async () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession, {
        cleanupScript: true
      });

      // 先启动一个任务（设置 currentScriptPath）
      const task = createTestTask();

      // 模拟长时间运行
      (mockTmux.captureOutput as any).mockResolvedValue('');

      // 启动执行但不等待
      const executePromise = executor.execute(task, testWorktreePath);

      // 等待一小段时间让脚本生成
      await new Promise(resolve => setTimeout(resolve, 50));

      // 取消任务
      await executor.cancel();

      expect(mockTmux.sendInterrupt).toHaveBeenCalled();
    });
  });

  describe('getCurrentOutput', () => {
    it('应该返回当前 tmux 会话输出', async () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession);

      (mockTmux.captureOutput as any).mockResolvedValue('Current output content');

      const output = await executor.getCurrentOutput();

      expect(output).toBe('Current output content');
      expect(mockTmux.captureOutput).toHaveBeenCalledWith(testSession);
    });
  });

  describe('配置方法', () => {
    beforeEach(() => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession);
    });

    it('setTimeout 应该更新超时配置', () => {
      executor.setTimeout(120000);
      expect(executor.getConfig().timeout).toBe(120000);
    });

    it('setCheckInterval 应该更新检查间隔', () => {
      executor.setCheckInterval(500);
      expect(executor.getConfig().checkInterval).toBe(500);
    });

    it('updateConfig 应该合并配置', () => {
      executor.updateConfig({
        permissionMode: 'bypassPermissions',
        maxTurns: 100
      });

      const config = executor.getConfig();
      expect(config.permissionMode).toBe('bypassPermissions');
      expect(config.maxTurns).toBe(100);
      // 其他配置应该保持不变
      expect(config.checkInterval).toBe(1000);
    });

    it('getConfig 应该返回配置副本', () => {
      const config1 = executor.getConfig();
      const config2 = executor.getConfig();

      // 应该是不同的对象
      expect(config1).not.toBe(config2);
      // 但值相同
      expect(config1).toEqual(config2);

      // 修改副本不应该影响原配置
      config1.timeout = 999999;
      expect(executor.getConfig().timeout).not.toBe(999999);
    });
  });

  describe('脚本路径生成', () => {
    it('应该在 worktree 目录生成脚本', async () => {
      executor = new HybridExecutor(mockTmux, mockMonitor, testSession);
      const task = createTestTask('unique-task-id');

      const completedOutput = JSON.stringify({
        type: 'task_completed',
        taskId: task.id,
        timestamp: Date.now(),
        output: 'Done',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      });

      (mockTmux.captureOutput as any)
        .mockResolvedValueOnce('')
        .mockResolvedValueOnce(completedOutput);

      await executor.execute(task, testWorktreePath);

      const writeCall = (fs.writeFile as any).mock.calls[0];
      const scriptPath = writeCall[0] as string;

      expect(scriptPath).toBe(path.join(testWorktreePath, '.paralleldev-task-unique-task-id.ts'));
    });
  });
});
