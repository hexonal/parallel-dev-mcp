/**
 * Agent 执行器 - 基于 Claude Agent SDK
 * @module parallel/worker/AgentExecutor
 *
 * 使用官方 @anthropic-ai/claude-agent-sdk 执行任务
 * 替代原有的 Tmux + CLI 方式
 */

import { query } from '@anthropic-ai/claude-agent-sdk';
import type {
  SDKMessage,
  Options,
  PermissionMode,
  HookCallbackMatcher
} from '@anthropic-ai/claude-agent-sdk';
import type { Task, TaskResult } from '../types';
import { createAgentHooks } from './agent-hooks';

/**
 * AgentExecutor 配置
 */
export interface AgentExecutorConfig {
  /** 权限模式 */
  permissionMode: PermissionMode;
  /** 允许的工具列表 */
  allowedTools: string[];
  /** 禁止的工具列表 */
  disallowedTools: string[];
  /** 超时时间（毫秒） */
  timeout: number;
  /** 最大对话轮数 */
  maxTurns?: number;
  /** Claude 模型 */
  model?: string;
  /** 是否加载项目设置 */
  loadProjectSettings: boolean;
  /** 是否启用 Hooks */
  enableHooks: boolean;
  /** 包含部分消息 */
  includePartialMessages: boolean;
}

/**
 * 默认配置
 */
const DEFAULT_CONFIG: AgentExecutorConfig = {
  permissionMode: 'acceptEdits',
  allowedTools: ['Read', 'Edit', 'Write', 'Bash', 'Grep', 'Glob', 'WebSearch'],
  disallowedTools: [],
  timeout: 600000,
  maxTurns: 50,
  loadProjectSettings: true,
  enableHooks: true,
  includePartialMessages: false
};

/**
 * 执行进度回调
 */
export interface ExecutionProgress {
  /** 消息类型 */
  type: 'assistant' | 'tool' | 'system' | 'progress';
  /** 消息内容 */
  content: string;
  /** 时间戳 */
  timestamp: number;
  /** 工具名称（如果是工具调用） */
  toolName?: string;
}

/**
 * AgentExecutor - 基于 Claude Agent SDK 的任务执行器
 */
export class AgentExecutor {
  private config: AgentExecutorConfig;
  private abortController: AbortController | null = null;
  private onProgress?: (progress: ExecutionProgress) => void;

  /**
   * 创建 AgentExecutor
   * @param config 执行器配置
   */
  constructor(config: Partial<AgentExecutorConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * 设置进度回调
   * @param callback 进度回调函数
   */
  setProgressCallback(callback: (progress: ExecutionProgress) => void): void {
    this.onProgress = callback;
  }

  /**
   * 执行任务
   * @param task 任务对象
   * @param worktreePath Worktree 工作目录
   * @returns 任务执行结果
   */
  async execute(task: Task, worktreePath: string): Promise<TaskResult> {
    const startTime = Date.now();
    this.abortController = new AbortController();

    try {
      // 1. 构建任务 Prompt
      const prompt = this.buildTaskPrompt(task);

      // 2. 构建 SDK Options
      const options = this.buildOptions(worktreePath);

      // 3. 执行查询
      const result = query({ prompt, options });

      // 4. 处理流式输出
      let output = '';
      let success = false;
      let errorMessage: string | undefined;
      let usage = {
        inputTokens: 0,
        outputTokens: 0,
        totalCost: 0
      };

      for await (const message of result) {
        const processed = this.processMessage(message);

        // 记录输出
        if (processed.output) {
          output += processed.output + '\n';
        }

        // 发送进度通知
        if (this.onProgress && processed.progress) {
          this.onProgress(processed.progress);
        }

        // 检测结果
        if (processed.isResult) {
          success = processed.success;
          errorMessage = processed.error;

          // 提取 usage 信息
          if (processed.usage) {
            usage = processed.usage;
          }
          break;
        }
      }

      const duration = Date.now() - startTime;

      return {
        success,
        output: output.trim(),
        error: errorMessage,
        duration,
        metadata: {
          usage,
          model: this.config.model,
          executor: 'agent-sdk'
        }
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMsg = error instanceof Error ? error.message : String(error);

      // 检查是否是中止错误
      if (this.abortController?.signal.aborted) {
        return {
          success: false,
          error: '任务被取消',
          duration
        };
      }

      return {
        success: false,
        error: errorMsg,
        duration
      };
    } finally {
      this.abortController = null;
    }
  }

  /**
   * 构建任务 Prompt
   */
  private buildTaskPrompt(task: Task): string {
    const parts = [
      '你是 ParallelDev Worker，正在执行分配给你的任务。',
      '',
      '## 任务信息',
      `- ID: ${task.id}`,
      `- 标题: ${task.title}`,
      `- 描述: ${task.description}`
    ];

    if (task.estimatedHours) {
      parts.push(`- 预估工时: ${task.estimatedHours} 小时`);
    }

    if (task.tags && task.tags.length > 0) {
      parts.push(`- 标签: ${task.tags.join(', ')}`);
    }

    parts.push(
      '',
      '## 执行要求',
      '1. 完成任务描述中的所有需求',
      '2. 遵循项目代码规范（查看 CLAUDE.md）',
      '3. 编写必要的测试（如适用）',
      '4. 确保代码质量（无 lint 错误、类型正确）',
      '5. 保持代码简洁，遵循 YAGNI 原则',
      '',
      '## 注意事项',
      '- 不要修改不相关的文件',
      '- 如有疑问，优先选择简单方案',
      '- 完成后提供简洁的完成摘要',
      '',
      '开始执行任务。'
    );

    return parts.join('\n');
  }

  /**
   * 构建 SDK Options
   */
  private buildOptions(worktreePath: string): Options {
    const hooks: Partial<Record<string, HookCallbackMatcher[]>> = {};

    if (this.config.enableHooks) {
      const agentHooks = createAgentHooks();
      hooks.PreToolUse = [{ hooks: [agentHooks.preToolUse] }];
      hooks.PostToolUse = [{ hooks: [agentHooks.postToolUse] }];
    }

    const options: Options = {
      cwd: worktreePath,
      permissionMode: this.config.permissionMode,
      allowedTools: this.config.allowedTools,
      disallowedTools: this.config.disallowedTools,
      abortController: this.abortController!,
      maxTurns: this.config.maxTurns,
      includePartialMessages: this.config.includePartialMessages,
      hooks
    };

    // 加载项目设置（包括 CLAUDE.md）
    if (this.config.loadProjectSettings) {
      options.settingSources = ['project'];
      options.systemPrompt = {
        type: 'preset',
        preset: 'claude_code'
      };
    }

    // 设置模型
    if (this.config.model) {
      options.model = this.config.model;
    }

    return options;
  }

  /**
   * 处理 SDK 消息
   */
  private processMessage(message: SDKMessage): {
    output?: string;
    progress?: ExecutionProgress;
    isResult: boolean;
    success: boolean;
    error?: string;
    usage?: {
      inputTokens: number;
      outputTokens: number;
      totalCost: number;
    };
  } {
    const timestamp = Date.now();

    switch (message.type) {
      case 'result': {
        const isSuccess = message.subtype === 'success';
        return {
          output: isSuccess ? (message as any).result : undefined,
          isResult: true,
          success: isSuccess,
          error: isSuccess ? undefined : `执行失败: ${message.subtype}`,
          usage: {
            inputTokens: (message as any).usage?.input_tokens ?? 0,
            outputTokens: (message as any).usage?.output_tokens ?? 0,
            totalCost: (message as any).total_cost_usd ?? 0
          }
        };
      }

      case 'assistant': {
        // 提取助手消息中的文本内容
        const textContents: string[] = [];
        for (const block of message.message.content) {
          if (block.type === 'text' && 'text' in block) {
            textContents.push((block as { type: 'text'; text: string }).text);
          }
        }

        const output = textContents.join('\n');

        return {
          output: output || undefined,
          progress: output
            ? {
                type: 'assistant',
                content: output,
                timestamp
              }
            : undefined,
          isResult: false,
          success: false
        };
      }

      case 'system': {
        if (message.subtype === 'init') {
          return {
            progress: {
              type: 'system',
              content: `会话初始化: model=${(message as any).model}`,
              timestamp
            },
            isResult: false,
            success: false
          };
        }
        return { isResult: false, success: false };
      }

      default:
        return { isResult: false, success: false };
    }
  }

  /**
   * 取消正在执行的任务
   */
  async cancel(): Promise<void> {
    if (this.abortController) {
      this.abortController.abort();
    }
  }

  /**
   * 检查是否正在执行
   */
  isRunning(): boolean {
    return this.abortController !== null;
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<AgentExecutorConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * 获取当前配置
   */
  getConfig(): AgentExecutorConfig {
    return { ...this.config };
  }
}
