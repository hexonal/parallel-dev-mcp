/**
 * 混合执行器 - 基于 Happy SDK 模式的任务执行
 * @module parallel/worker/HybridExecutor
 *
 * 重构版本：使用 WorkerClaudeRunner 通过 stdin/stdout 与 Claude Code 交互
 * 参考 happy-cli 的 SDK 模式，而非生成脚本执行
 */

import { Task, TaskResult } from '../types';
import { TmuxController } from '../tmux/TmuxController';
import { SessionMonitor } from '../tmux/SessionMonitor';
import {
  WorkerClaudeRunner,
  WorkerClaudeRunnerConfig,
  SDKMessage
} from './WorkerClaudeRunner';

/**
 * HybridExecutor 配置
 */
export interface HybridExecutorConfig {
  /** 超时时间（毫秒） */
  timeout: number;
  /** 权限模式 */
  permissionMode: 'default' | 'acceptEdits' | 'bypassPermissions';
  /** 允许的工具 */
  allowedTools: string[];
  /** 禁止的工具 */
  disallowedTools: string[];
  /** 最大对话轮数 */
  maxTurns: number;
  /** 是否启用 Hooks */
  enableHooks: boolean;
  /** Claude 模型 */
  model?: string;
  /** 自定义环境变量 */
  env?: Record<string, string>;
}

/**
 * 默认配置
 */
const DEFAULT_CONFIG: HybridExecutorConfig = {
  timeout: 600000,
  permissionMode: 'acceptEdits',
  allowedTools: ['Read', 'Edit', 'Write', 'Bash', 'Grep', 'Glob', 'WebSearch'],
  disallowedTools: [],
  maxTurns: 50,
  enableHooks: true,
  model: undefined,
  env: undefined
};

/**
 * HybridExecutor - 基于 Happy SDK 模式的混合执行器
 *
 * 执行流程：
 * 1. 创建 WorkerClaudeRunner（spawn Claude CLI）
 * 2. 通过 stdin 发送任务 prompt
 * 3. 监听 stdout 的 JSON 消息
 * 4. 等待 result 消息返回结果
 */
export class HybridExecutor {
  private tmux: TmuxController;
  private monitor: SessionMonitor;
  private tmuxSession: string;
  private config: HybridExecutorConfig;
  private currentRunner: WorkerClaudeRunner | null = null;

  /**
   * 创建 HybridExecutor
   */
  constructor(
    tmux: TmuxController,
    monitor: SessionMonitor,
    tmuxSession: string,
    config: Partial<HybridExecutorConfig> = {}
  ) {
    this.tmux = tmux;
    this.monitor = monitor;
    this.tmuxSession = tmuxSession;
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * 执行任务
   *
   * 执行流程（基于 Claude CLI stream-json 模式）：
   * 1. spawn Claude CLI
   * 2. 立即发送任务 prompt（CLI 需要 stdin 输入才会输出 init）
   * 3. 等待 result 消息
   */
  async execute(task: Task, worktreePath: string): Promise<TaskResult> {
    const startTime = Date.now();

    try {
      // 1. 创建 WorkerClaudeRunner
      const runnerConfig = this.buildRunnerConfig(worktreePath);
      const runner = new WorkerClaudeRunner(runnerConfig);
      this.currentRunner = runner;

      // 2. 启动 Runner
      await runner.start();

      // 3. 立即发送任务 prompt
      // 注意：Claude CLI 在 stream-json 模式下需要先收到 stdin 输入才会输出 init 消息
      const prompt = this.buildTaskPrompt(task);
      runner.sendMessage(prompt);

      // 4. 等待任务完成
      const result = await this.waitForResult(runner, task.id, startTime);

      // 5. 停止 Runner
      runner.stop();
      this.currentRunner = null;

      return result;
    } catch (error) {
      // 清理
      if (this.currentRunner) {
        this.currentRunner.stop();
        this.currentRunner = null;
      }

      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
        duration: Date.now() - startTime,
        metadata: { executor: 'hybrid-sdk' }
      };
    }
  }

  /**
   * 构建 Runner 配置
   */
  private buildRunnerConfig(worktreePath: string): WorkerClaudeRunnerConfig {
    return {
      workingDir: worktreePath,
      permissionMode: this.config.permissionMode,
      model: this.config.model,
      timeout: this.config.timeout,
      maxTurns: this.config.maxTurns,
      allowedTools: this.config.allowedTools,
      disallowedTools: this.config.disallowedTools
    };
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
   * 等待任务结果
   */
  private waitForResult(
    runner: WorkerClaudeRunner,
    taskId: string,
    startTime: number
  ): Promise<TaskResult> {
    return new Promise((resolve, reject) => {
      // 设置超时
      const timeout = setTimeout(() => {
        runner.interrupt().catch(() => {});
        reject(new Error(`任务 ${taskId} 执行超时 (${this.config.timeout}ms)`));
      }, this.config.timeout);

      // 监听结果消息
      const handleMessage = (message: SDKMessage) => {
        if (message.type === 'result') {
          clearTimeout(timeout);
          runner.off('message', handleMessage);

          const isSuccess = message.subtype === 'success';
          const output = runner.getCollectedOutput().join('\n');

          // 提取 usage 信息
          const msgAny = message as Record<string, unknown>;
          const usage = {
            inputTokens: 0,
            outputTokens: 0,
            totalCost: 0
          };

          if (msgAny.usage && typeof msgAny.usage === 'object') {
            const u = msgAny.usage as Record<string, unknown>;
            usage.inputTokens = (u.input_tokens as number) ?? 0;
            usage.outputTokens = (u.output_tokens as number) ?? 0;
          }

          if (typeof msgAny.total_cost_usd === 'number') {
            usage.totalCost = msgAny.total_cost_usd;
          }

          if (isSuccess) {
            resolve({
              success: true,
              output: (msgAny.result as string) || output,
              duration: Date.now() - startTime,
              metadata: {
                usage,
                executor: 'hybrid-sdk',
                sessionId: runner.getSessionId()
              }
            });
          } else {
            resolve({
              success: false,
              error: `执行失败: ${message.subtype}`,
              duration: Date.now() - startTime,
              metadata: { executor: 'hybrid-sdk' }
            });
          }
        }
      };

      runner.on('message', handleMessage);

      // 监听错误
      runner.once('error', (error) => {
        clearTimeout(timeout);
        runner.off('message', handleMessage);
        reject(error);
      });

      // 监听进程退出
      runner.once('exit', (code) => {
        clearTimeout(timeout);
        runner.off('message', handleMessage);

        // 检查是否已经有结果
        const lastResult = runner.getLastResult();
        if (lastResult && lastResult.subtype === 'success') {
          return;
        }

        if (code !== 0) {
          reject(new Error(`Claude Code 进程异常退出 (code: ${code})`));
        }
      });
    });
  }

  /**
   * 取消正在执行的任务
   */
  async cancel(): Promise<void> {
    if (this.currentRunner) {
      await this.currentRunner.interrupt().catch(() => {});
      this.currentRunner.stop();
      this.currentRunner = null;
    }
  }

  /**
   * 检查是否有任务在执行
   */
  isExecuting(): boolean {
    return this.currentRunner !== null && this.currentRunner.isActive();
  }

  /**
   * 获取当前会话 ID
   */
  getCurrentSessionId(): string | null {
    return this.currentRunner?.getSessionId() ?? null;
  }

  /**
   * 设置超时时间
   */
  setTimeout(timeoutMs: number): void {
    this.config.timeout = timeoutMs;
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<HybridExecutorConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * 获取当前配置
   */
  getConfig(): HybridExecutorConfig {
    return { ...this.config };
  }
}
