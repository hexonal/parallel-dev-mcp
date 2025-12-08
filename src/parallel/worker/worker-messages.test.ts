/**
 * Worker 消息类型单元测试
 * @module parallel/worker/worker-messages.test
 */

import { describe, it, expect } from 'vitest';
import {
  parseWorkerMessage,
  serializeMessage,
  createInitMessage,
  createSdkMessage,
  createProgressMessage,
  createTaskCompletedMessage,
  createTaskFailedMessage,
  isCompletedMessage,
  isFailedMessage,
  isTerminalMessage,
  WorkerMessage,
  InitMessage,
  SdkMessage,
  ProgressMessage,
  TaskCompletedMessage,
  TaskFailedMessage,
  TokenUsage
} from './worker-messages';

describe('worker-messages', () => {
  describe('parseWorkerMessage', () => {
    it('应该正确解析有效的 init 消息', () => {
      const json = JSON.stringify({
        type: 'init',
        taskId: 'task-001',
        timestamp: 1702345678901,
        worktreePath: '/path/to/worktree',
        model: 'claude-3'
      });

      const result = parseWorkerMessage(json);

      expect(result).not.toBeNull();
      expect(result?.type).toBe('init');
      expect(result?.taskId).toBe('task-001');
      expect((result as InitMessage).worktreePath).toBe('/path/to/worktree');
    });

    it('应该正确解析有效的 sdk_message 消息', () => {
      const json = JSON.stringify({
        type: 'sdk_message',
        taskId: 'task-001',
        timestamp: 1702345678901,
        sdkType: 'assistant',
        content: 'Hello, world!'
      });

      const result = parseWorkerMessage(json);

      expect(result).not.toBeNull();
      expect(result?.type).toBe('sdk_message');
      expect((result as SdkMessage).sdkType).toBe('assistant');
      expect((result as SdkMessage).content).toBe('Hello, world!');
    });

    it('应该正确解析有效的 progress 消息', () => {
      const json = JSON.stringify({
        type: 'progress',
        taskId: 'task-001',
        timestamp: 1702345678901,
        phase: 'coding',
        detail: 'Editing src/index.ts'
      });

      const result = parseWorkerMessage(json);

      expect(result).not.toBeNull();
      expect(result?.type).toBe('progress');
      expect((result as ProgressMessage).phase).toBe('coding');
      expect((result as ProgressMessage).detail).toBe('Editing src/index.ts');
    });

    it('应该正确解析有效的 task_completed 消息', () => {
      const json = JSON.stringify({
        type: 'task_completed',
        taskId: 'task-001',
        timestamp: 1702345678901,
        output: 'Task completed successfully',
        usage: {
          inputTokens: 1000,
          outputTokens: 500,
          totalCost: 0.015
        }
      });

      const result = parseWorkerMessage(json);

      expect(result).not.toBeNull();
      expect(result?.type).toBe('task_completed');
      expect((result as TaskCompletedMessage).output).toBe('Task completed successfully');
      expect((result as TaskCompletedMessage).usage.inputTokens).toBe(1000);
    });

    it('应该正确解析有效的 task_failed 消息', () => {
      const json = JSON.stringify({
        type: 'task_failed',
        taskId: 'task-001',
        timestamp: 1702345678901,
        error: 'Something went wrong',
        errorCode: 'ERR_001'
      });

      const result = parseWorkerMessage(json);

      expect(result).not.toBeNull();
      expect(result?.type).toBe('task_failed');
      expect((result as TaskFailedMessage).error).toBe('Something went wrong');
      expect((result as TaskFailedMessage).errorCode).toBe('ERR_001');
    });

    it('对于空行应该返回 null', () => {
      expect(parseWorkerMessage('')).toBeNull();
      expect(parseWorkerMessage('   ')).toBeNull();
      expect(parseWorkerMessage('\n')).toBeNull();
    });

    it('对于非 JSON 格式应该返回 null', () => {
      expect(parseWorkerMessage('not json')).toBeNull();
      expect(parseWorkerMessage('{ incomplete')).toBeNull();
      expect(parseWorkerMessage('plain text message')).toBeNull();
    });

    it('对于缺少必要字段的 JSON 应该返回 null', () => {
      // 缺少 type
      expect(parseWorkerMessage(JSON.stringify({
        taskId: 'task-001',
        timestamp: 1702345678901
      }))).toBeNull();

      // 缺少 taskId
      expect(parseWorkerMessage(JSON.stringify({
        type: 'init',
        timestamp: 1702345678901
      }))).toBeNull();

      // 缺少 timestamp
      expect(parseWorkerMessage(JSON.stringify({
        type: 'init',
        taskId: 'task-001'
      }))).toBeNull();
    });

    it('对于无效的消息类型应该返回 null', () => {
      const json = JSON.stringify({
        type: 'unknown_type',
        taskId: 'task-001',
        timestamp: 1702345678901
      });

      expect(parseWorkerMessage(json)).toBeNull();
    });

    it('应该正确处理带有前后空格的 JSON', () => {
      const json = '  {"type":"init","taskId":"task-001","timestamp":1702345678901,"worktreePath":"/path"}  ';

      const result = parseWorkerMessage(json);

      expect(result).not.toBeNull();
      expect(result?.type).toBe('init');
    });
  });

  describe('serializeMessage', () => {
    it('应该正确序列化消息', () => {
      const message: InitMessage = {
        type: 'init',
        taskId: 'task-001',
        timestamp: 1702345678901,
        worktreePath: '/path/to/worktree'
      };

      const serialized = serializeMessage(message);
      const parsed = JSON.parse(serialized);

      expect(parsed.type).toBe('init');
      expect(parsed.taskId).toBe('task-001');
      expect(parsed.worktreePath).toBe('/path/to/worktree');
    });

    it('序列化后应该能被 parseWorkerMessage 正确解析', () => {
      const message: TaskCompletedMessage = {
        type: 'task_completed',
        taskId: 'task-001',
        timestamp: Date.now(),
        output: 'Success',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      };

      const serialized = serializeMessage(message);
      const parsed = parseWorkerMessage(serialized);

      expect(parsed).not.toBeNull();
      expect(parsed?.type).toBe('task_completed');
      expect((parsed as TaskCompletedMessage).output).toBe('Success');
    });
  });

  describe('createInitMessage', () => {
    it('应该创建正确的初始化消息', () => {
      const message = createInitMessage('task-001', '/path/to/worktree', 'claude-3');

      expect(message.type).toBe('init');
      expect(message.taskId).toBe('task-001');
      expect(message.worktreePath).toBe('/path/to/worktree');
      expect(message.model).toBe('claude-3');
      expect(typeof message.timestamp).toBe('number');
    });

    it('model 参数应该是可选的', () => {
      const message = createInitMessage('task-001', '/path/to/worktree');

      expect(message.type).toBe('init');
      expect(message.model).toBeUndefined();
    });
  });

  describe('createSdkMessage', () => {
    it('应该创建正确的 SDK 消息', () => {
      const message = createSdkMessage('task-001', 'assistant', 'Hello', 'Read');

      expect(message.type).toBe('sdk_message');
      expect(message.taskId).toBe('task-001');
      expect(message.sdkType).toBe('assistant');
      expect(message.content).toBe('Hello');
      expect(message.toolName).toBe('Read');
    });

    it('content 和 toolName 应该是可选的', () => {
      const message = createSdkMessage('task-001', 'system');

      expect(message.type).toBe('sdk_message');
      expect(message.content).toBeUndefined();
      expect(message.toolName).toBeUndefined();
    });
  });

  describe('createProgressMessage', () => {
    it('应该创建正确的进度消息', () => {
      const message = createProgressMessage('task-001', 'coding', 'Working on feature');

      expect(message.type).toBe('progress');
      expect(message.taskId).toBe('task-001');
      expect(message.phase).toBe('coding');
      expect(message.detail).toBe('Working on feature');
    });
  });

  describe('createTaskCompletedMessage', () => {
    it('应该创建正确的完成消息', () => {
      const usage: TokenUsage = {
        inputTokens: 1000,
        outputTokens: 500,
        totalCost: 0.015
      };

      const message = createTaskCompletedMessage('task-001', 'Done!', usage);

      expect(message.type).toBe('task_completed');
      expect(message.taskId).toBe('task-001');
      expect(message.output).toBe('Done!');
      expect(message.usage).toEqual(usage);
    });
  });

  describe('createTaskFailedMessage', () => {
    it('应该创建正确的失败消息', () => {
      const message = createTaskFailedMessage(
        'task-001',
        'Error occurred',
        'ERR_001',
        'Error stack trace'
      );

      expect(message.type).toBe('task_failed');
      expect(message.taskId).toBe('task-001');
      expect(message.error).toBe('Error occurred');
      expect(message.errorCode).toBe('ERR_001');
      expect(message.stack).toBe('Error stack trace');
    });

    it('errorCode 和 stack 应该是可选的', () => {
      const message = createTaskFailedMessage('task-001', 'Error occurred');

      expect(message.type).toBe('task_failed');
      expect(message.errorCode).toBeUndefined();
      expect(message.stack).toBeUndefined();
    });
  });

  describe('isCompletedMessage', () => {
    it('对于 task_completed 消息应该返回 true', () => {
      const message: TaskCompletedMessage = {
        type: 'task_completed',
        taskId: 'task-001',
        timestamp: Date.now(),
        output: 'Done',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      };

      expect(isCompletedMessage(message)).toBe(true);
    });

    it('对于其他类型消息应该返回 false', () => {
      const initMessage: InitMessage = {
        type: 'init',
        taskId: 'task-001',
        timestamp: Date.now(),
        worktreePath: '/path'
      };

      const failedMessage: TaskFailedMessage = {
        type: 'task_failed',
        taskId: 'task-001',
        timestamp: Date.now(),
        error: 'Error'
      };

      expect(isCompletedMessage(initMessage)).toBe(false);
      expect(isCompletedMessage(failedMessage)).toBe(false);
    });
  });

  describe('isFailedMessage', () => {
    it('对于 task_failed 消息应该返回 true', () => {
      const message: TaskFailedMessage = {
        type: 'task_failed',
        taskId: 'task-001',
        timestamp: Date.now(),
        error: 'Error'
      };

      expect(isFailedMessage(message)).toBe(true);
    });

    it('对于其他类型消息应该返回 false', () => {
      const initMessage: InitMessage = {
        type: 'init',
        taskId: 'task-001',
        timestamp: Date.now(),
        worktreePath: '/path'
      };

      const completedMessage: TaskCompletedMessage = {
        type: 'task_completed',
        taskId: 'task-001',
        timestamp: Date.now(),
        output: 'Done',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      };

      expect(isFailedMessage(initMessage)).toBe(false);
      expect(isFailedMessage(completedMessage)).toBe(false);
    });
  });

  describe('isTerminalMessage', () => {
    it('对于 task_completed 消息应该返回 true', () => {
      const message: TaskCompletedMessage = {
        type: 'task_completed',
        taskId: 'task-001',
        timestamp: Date.now(),
        output: 'Done',
        usage: { inputTokens: 100, outputTokens: 50, totalCost: 0.01 }
      };

      expect(isTerminalMessage(message)).toBe(true);
    });

    it('对于 task_failed 消息应该返回 true', () => {
      const message: TaskFailedMessage = {
        type: 'task_failed',
        taskId: 'task-001',
        timestamp: Date.now(),
        error: 'Error'
      };

      expect(isTerminalMessage(message)).toBe(true);
    });

    it('对于非终结消息应该返回 false', () => {
      const initMessage: InitMessage = {
        type: 'init',
        taskId: 'task-001',
        timestamp: Date.now(),
        worktreePath: '/path'
      };

      const progressMessage: ProgressMessage = {
        type: 'progress',
        taskId: 'task-001',
        timestamp: Date.now(),
        phase: 'coding',
        detail: 'Working'
      };

      const sdkMessage: SdkMessage = {
        type: 'sdk_message',
        taskId: 'task-001',
        timestamp: Date.now(),
        sdkType: 'assistant',
        content: 'Hello'
      };

      expect(isTerminalMessage(initMessage)).toBe(false);
      expect(isTerminalMessage(progressMessage)).toBe(false);
      expect(isTerminalMessage(sdkMessage)).toBe(false);
    });
  });

  describe('消息往返测试', () => {
    it('所有消息类型都应该能正确序列化和反序列化', () => {
      const messages: WorkerMessage[] = [
        createInitMessage('task-001', '/path', 'claude-3'),
        createSdkMessage('task-001', 'assistant', 'Hello'),
        createProgressMessage('task-001', 'coding', 'Working'),
        createTaskCompletedMessage('task-001', 'Done', {
          inputTokens: 100,
          outputTokens: 50,
          totalCost: 0.01
        }),
        createTaskFailedMessage('task-001', 'Error', 'ERR_001')
      ];

      for (const original of messages) {
        const serialized = serializeMessage(original);
        const parsed = parseWorkerMessage(serialized);

        expect(parsed).not.toBeNull();
        expect(parsed?.type).toBe(original.type);
        expect(parsed?.taskId).toBe(original.taskId);
      }
    });
  });
});
