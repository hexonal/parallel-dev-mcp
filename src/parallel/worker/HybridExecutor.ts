/**
 * 混合执行器 - Tmux + WorkerRunner 并行执行
 * @module parallel/worker/HybridExecutor
 *
 * 核心架构：每个 Worker 在独立 Tmux 会话中运行 WorkerRunner
 * WorkerRunner 使用 AgentExecutor 执行任务，通过 Socket.IO 报告状态
 *
 * 执行模式：
 * - useWorkerRunner=true（默认）: 使用 WorkerRunner + AgentExecutor
 * - useWorkerRunner=false: 使用原有 Claude CLI 方式（保留兼容）
 */

import * as path from 'path';
import * as fs from 'fs/promises';
import { Task, TaskResult } from '../types';
import { TmuxController } from '../tmux/TmuxController';
import { SessionMonitor } from '../tmux/SessionMonitor';
import { WorkerRunnerConfig, GitConfig } from './WorkerRunner';

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
  /** 监控检查间隔（毫秒） */
  monitorInterval: number;
  /** Master Socket.IO 端口（WorkerRunner 模式需要） */
  masterPort?: number;
  /** 是否使用 WorkerRunner 模式（默认 true） */
  useWorkerRunner?: boolean;
  /** Git 配置（WorkerRunner 模式） */
  gitConfig?: GitConfig;
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
  env: undefined,
  monitorInterval: 2000,
  masterPort: 3001,
  useWorkerRunner: true,
  gitConfig: {
    autoCommit: true,
    autoPush: true,
    autoMerge: true,  // 默认启用自动合并，Worker 完成后通知 Master 执行合并
  },
};

/**
 * HybridExecutor - Tmux + WorkerRunner 混合执行器
 *
 * 核心执行流程（WorkerRunner 模式）：
 * 1. 确保 Tmux 会话存在
 * 2. 生成 WorkerRunner 配置文件
 * 3. 在 Tmux 会话中启动 WorkerRunner
 * 4. WorkerRunner 通过 Socket.IO 向 Master 报告状态
 *
 * 可观察性：用户可通过 `tmux attach -t <session>` 实时查看执行
 */
export class HybridExecutor {
  private tmux: TmuxController;
  private monitor: SessionMonitor;
  private tmuxSessionId: string;
  private config: HybridExecutorConfig;
  private isClaudeStarted: boolean = false;
  private currentSessionName: string | null = null;

  /**
   * 创建 HybridExecutor
   * @param tmux TmuxController 实例
   * @param monitor SessionMonitor 实例
   * @param tmuxSessionId 会话 ID（不含前缀）
   * @param config 执行器配置
   */
  constructor(
    tmux: TmuxController,
    monitor: SessionMonitor,
    tmuxSessionId: string,
    config: Partial<HybridExecutorConfig> = {}
  ) {
    this.tmux = tmux;
    this.monitor = monitor;
    this.tmuxSessionId = tmuxSessionId;
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * 执行任务
   *
   * 在 Tmux 会话中运行 WorkerRunner 或 Claude CLI 执行任务
   * @param task 任务
   * @param worktreePath worktree 路径
   * @param fireAndForget 如果为 true，只启动不等待结果
   */
  async execute(
    task: Task,
    worktreePath: string,
    fireAndForget: boolean = false
  ): Promise<TaskResult> {
    const startTime = Date.now();

    try {
      // 1. 确保 Tmux 会话存在
      await this.ensureTmuxSession(worktreePath);

      // 2. 根据配置选择执行模式
      if (this.config.useWorkerRunner) {
        // WorkerRunner 模式
        return await this.executeWithWorkerRunner(task, worktreePath, fireAndForget, startTime);
      } else {
        // 原有 Claude CLI 模式（保留兼容）
        return await this.executeWithClaudeCLI(task, worktreePath, fireAndForget, startTime);
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
        duration: Date.now() - startTime,
        metadata: { executor: this.config.useWorkerRunner ? 'worker-runner' : 'hybrid-tmux' }
      };
    }
  }

  /**
   * 使用 WorkerRunner 执行任务
   */
  private async executeWithWorkerRunner(
    task: Task,
    worktreePath: string,
    fireAndForget: boolean,
    startTime: number
  ): Promise<TaskResult> {
    // 1. 启动 WorkerRunner
    await this.startWorkerRunnerInTmux(task, worktreePath);

    // 2. Fire-and-forget 模式：启动后立即返回
    if (fireAndForget) {
      return {
        success: true,
        output: 'WorkerRunner started in background',
        duration: Date.now() - startTime,
        metadata: {
          executor: 'worker-runner',
          mode: 'fire-and-forget',
          sessionName: this.currentSessionName
        }
      };
    }

    // 3. 等待模式：监控输出等待结果
    // 注意：WorkerRunner 模式下，结果通过 Socket.IO 报告给 Master
    // 这里只是等待进程结束
    const result = await this.waitForWorkerRunnerComplete(task.id, startTime);
    return result;
  }

  /**
   * 使用原有 Claude CLI 执行任务
   */
  private async executeWithClaudeCLI(
    task: Task,
    worktreePath: string,
    fireAndForget: boolean,
    startTime: number
  ): Promise<TaskResult> {
    // 1. 在 Tmux 会话中启动 Claude CLI（如果未启动）
    await this.startClaudeInTmux();

    // 2. 构建并发送任务消息
    const prompt = this.buildTaskPrompt(task);
    await this.sendJsonMessage(prompt);

    // 3. Fire-and-forget 模式：启动后立即返回
    if (fireAndForget) {
      return {
        success: true,
        output: 'Task started in background',
        duration: Date.now() - startTime,
        metadata: {
          executor: 'hybrid-tmux',
          mode: 'fire-and-forget',
          sessionName: this.currentSessionName
        }
      };
    }

    // 4. 监控输出，等待结果
    const result = await this.waitForResultViaTmux(task.id, startTime);
    return result;
  }

  /**
   * 确保 Tmux 会话存在
   */
  private async ensureTmuxSession(worktreePath: string): Promise<void> {
    const sessionName = this.tmux.getSessionName(this.tmuxSessionId);

    if (!this.tmux.sessionExists(sessionName)) {
      await this.tmux.createSession(this.tmuxSessionId, worktreePath);
      this.isClaudeStarted = false;
    }

    this.currentSessionName = sessionName;
  }

  /**
   * 在 Tmux 会话中启动 Claude CLI
   */
  private async startClaudeInTmux(): Promise<void> {
    if (!this.currentSessionName) {
      throw new Error('Tmux 会话未初始化');
    }

    if (this.isClaudeStarted) {
      return;
    }

    // 构建 Claude CLI 命令
    const claudeCmd = this.buildClaudeCommand();

    // 发送启动命令
    await this.tmux.sendCommand(this.currentSessionName, claudeCmd);

    // 等待 Claude 启动就绪
    await this.waitForClaudeReady();

    this.isClaudeStarted = true;
  }

  /**
   * 构建 Claude CLI 启动命令
   */
  private buildClaudeCommand(): string {
    const args = [
      'claude',
      '--input-format', 'stream-json',
      '--output-format', 'stream-json',
      '--verbose'
    ];

    // 权限模式
    if (this.config.permissionMode) {
      args.push('--permission-mode', this.config.permissionMode);
    }

    // 模型
    if (this.config.model) {
      args.push('--model', this.config.model);
    }

    // 最大轮数
    if (this.config.maxTurns) {
      args.push('--max-turns', this.config.maxTurns.toString());
    }

    // 允许的工具
    if (this.config.allowedTools && this.config.allowedTools.length > 0) {
      args.push('--allowedTools', this.config.allowedTools.join(','));
    }

    // 禁止的工具
    if (this.config.disallowedTools && this.config.disallowedTools.length > 0) {
      args.push('--disallowedTools', this.config.disallowedTools.join(','));
    }

    return args.join(' ');
  }

  /**
   * 等待 Claude CLI 启动就绪
   */
  private async waitForClaudeReady(): Promise<void> {
    if (!this.currentSessionName) {
      throw new Error('Tmux 会话未初始化');
    }

    const maxWaitTime = 30000;
    const startTime = Date.now();
    const checkInterval = 500;

    while (Date.now() - startTime < maxWaitTime) {
      const output = await this.tmux.captureOutput(this.currentSessionName);

      // Claude CLI 启动后会显示等待输入的状态
      // stream-json 模式下需要发送第一条消息才会输出 init
      // 检查是否已经启动（没有错误信息）
      if (!output.includes('Error') && !output.includes('command not found')) {
        // 给 Claude 一点启动时间
        await this.sleep(1000);
        return;
      }

      if (output.includes('Error') || output.includes('command not found')) {
        throw new Error(`Claude CLI 启动失败: ${output}`);
      }

      await this.sleep(checkInterval);
    }

    throw new Error('Claude CLI 启动超时');
  }

  /**
   * 发送 JSON 消息到 Claude CLI
   */
  private async sendJsonMessage(content: string): Promise<void> {
    if (!this.currentSessionName) {
      throw new Error('Tmux 会话未初始化');
    }

    const message = JSON.stringify({
      type: 'user',
      message: {
        role: 'user',
        content
      }
    });

    // 通过 Tmux 发送 JSON 消息
    await this.tmux.sendCommand(this.currentSessionName, message);
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
   * 通过 Tmux 监控等待任务结果
   */
  private async waitForResultViaTmux(
    taskId: string,
    startTime: number
  ): Promise<TaskResult> {
    if (!this.currentSessionName) {
      throw new Error('Tmux 会话未初始化');
    }

    const sessionName = this.currentSessionName;
    let lastOutputLength = 0;
    let collectedOutput: string[] = [];

    return new Promise((resolve, reject) => {
      const checkInterval = setInterval(async () => {
        try {
          const output = await this.tmux.captureOutput(sessionName);

          // 检查新输出
          if (output.length > lastOutputLength) {
            const newContent = output.slice(lastOutputLength);
            lastOutputLength = output.length;

            // 解析 JSON 消息
            const lines = newContent.split('\n');
            for (const line of lines) {
              const trimmedLine = line.trim();
              if (!trimmedLine) continue;

              // 尝试解析 JSON
              if (trimmedLine.startsWith('{')) {
                try {
                  const message = JSON.parse(trimmedLine);

                  // 收集 assistant 输出
                  if (message.type === 'assistant' && message.message?.content) {
                    const content = this.extractTextFromMessage(message);
                    if (content) {
                      collectedOutput.push(content);
                    }
                  }

                  // 检测 result 消息
                  if (message.type === 'result') {
                    clearInterval(checkInterval);

                    const isSuccess = message.subtype === 'success';
                    const finalOutput = collectedOutput.join('\n');

                    // 提取 usage 信息
                    const usage = this.extractUsageFromResult(message);

                    resolve({
                      success: isSuccess,
                      output: message.result || finalOutput,
                      duration: Date.now() - startTime,
                      metadata: {
                        usage,
                        executor: 'hybrid-tmux',
                        sessionId: message.session_id
                      }
                    });
                    return;
                  }
                } catch {
                  // 不是有效 JSON，忽略
                }
              }
            }
          }

          // 超时检查
          if (Date.now() - startTime > this.config.timeout) {
            clearInterval(checkInterval);
            reject(new Error(`任务 ${taskId} 执行超时 (${this.config.timeout}ms)`));
          }
        } catch (error) {
          clearInterval(checkInterval);
          reject(error);
        }
      }, this.config.monitorInterval);
    });
  }

  /**
   * 从消息中提取文本内容
   */
  private extractTextFromMessage(message: Record<string, unknown>): string | null {
    const msgContent = message.message as Record<string, unknown> | undefined;
    if (!msgContent) return null;

    const content = msgContent.content;
    if (typeof content === 'string') {
      return content;
    }

    if (Array.isArray(content)) {
      const textParts: string[] = [];
      for (const block of content) {
        if (block.type === 'text' && typeof block.text === 'string') {
          textParts.push(block.text);
        }
      }
      return textParts.length > 0 ? textParts.join('\n') : null;
    }

    return null;
  }

  /**
   * 从 result 消息中提取 usage 信息
   */
  private extractUsageFromResult(message: Record<string, unknown>): {
    inputTokens: number;
    outputTokens: number;
    totalCost: number;
  } {
    const usage = {
      inputTokens: 0,
      outputTokens: 0,
      totalCost: 0
    };

    if (message.usage && typeof message.usage === 'object') {
      const u = message.usage as Record<string, unknown>;
      usage.inputTokens = (u.input_tokens as number) ?? 0;
      usage.outputTokens = (u.output_tokens as number) ?? 0;
    }

    if (typeof message.total_cost_usd === 'number') {
      usage.totalCost = message.total_cost_usd;
    }

    return usage;
  }

  /**
   * 睡眠辅助函数
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 取消正在执行的任务
   */
  async cancel(): Promise<void> {
    if (this.currentSessionName) {
      // 发送 Ctrl+C 中断
      await this.tmux.sendInterrupt(this.currentSessionName);
      this.isClaudeStarted = false;
    }
  }

  /**
   * 检查是否有任务在执行
   */
  isExecuting(): boolean {
    if (!this.currentSessionName) {
      return false;
    }
    return this.tmux.sessionExists(this.currentSessionName) && this.isClaudeStarted;
  }

  /**
   * 获取当前 Tmux 会话名称
   */
  getCurrentSessionName(): string | null {
    return this.currentSessionName;
  }

  /**
   * 获取 Tmux 会话 ID（不含前缀）
   */
  getSessionId(): string {
    return this.tmuxSessionId;
  }

  /**
   * 关闭 Tmux 会话
   */
  async closeSession(): Promise<void> {
    if (this.currentSessionName) {
      await this.tmux.killSession(this.currentSessionName);
      this.currentSessionName = null;
      this.isClaudeStarted = false;
    }
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

  /**
   * 获取 Tmux 会话输出（用于调试）
   */
  async getSessionOutput(lines: number = 100): Promise<string | null> {
    if (!this.currentSessionName) {
      return null;
    }
    return this.tmux.captureOutput(this.currentSessionName, lines);
  }

  // ============ WorkerRunner 模式方法 ============

  /**
   * 在 Tmux 会话中启动 WorkerRunner
   */
  private async startWorkerRunnerInTmux(task: Task, worktreePath: string): Promise<void> {
    if (!this.currentSessionName) {
      throw new Error('Tmux 会话未初始化');
    }

    // 1. 创建配置文件
    const configPath = `/tmp/pdev-worker-${task.id}.json`;
    const config: WorkerRunnerConfig = {
      workerId: `worker-${task.id}`,
      masterEndpoint: `http://localhost:${this.config.masterPort}`,
      worktreePath,
      task,
      executorConfig: {
        permissionMode: this.config.permissionMode,
        timeout: this.config.timeout,
        maxTurns: this.config.maxTurns,
        allowedTools: this.config.allowedTools,
        disallowedTools: this.config.disallowedTools,
        loadProjectSettings: true,
        enableHooks: this.config.enableHooks,
      },
      gitConfig: this.config.gitConfig,
    };

    // 写入配置文件
    await fs.writeFile(configPath, JSON.stringify(config, null, 2));

    // 2. 构建启动命令
    // __dirname 在运行时指向 dist 目录，使用 .js 后缀
    const entryPath = path.resolve(__dirname, 'worker-runner-entry.js');
    const command = `node "${entryPath}" --config="${configPath}"`;

    // 3. 在 Tmux 中执行
    await this.tmux.sendCommand(this.currentSessionName, command);

    // 4. 等待 WorkerRunner 启动（检查进程启动）
    await this.waitForWorkerRunnerStarted();
  }

  /**
   * 等待 WorkerRunner 启动
   */
  private async waitForWorkerRunnerStarted(): Promise<void> {
    if (!this.currentSessionName) {
      throw new Error('Tmux 会话未初始化');
    }

    const maxWaitTime = 10000; // 10秒
    const startTime = Date.now();
    const checkInterval = 500;

    while (Date.now() - startTime < maxWaitTime) {
      const output = await this.tmux.captureOutput(this.currentSessionName);

      // 检查 WorkerRunner 启动标志
      if (output.includes('[WorkerRunner]') || output.includes('[worker-runner-entry]')) {
        // WorkerRunner 已启动
        return;
      }

      // 检查错误
      if (output.includes('Error:') && output.includes('worker-runner')) {
        throw new Error(`WorkerRunner 启动失败: ${output}`);
      }

      await this.sleep(checkInterval);
    }

    // 超时但没有错误，假设正在启动
    // 实际状态由 Socket.IO 报告
  }

  /**
   * 等待 WorkerRunner 完成（同步模式）
   */
  private async waitForWorkerRunnerComplete(
    taskId: string,
    startTime: number
  ): Promise<TaskResult> {
    if (!this.currentSessionName) {
      throw new Error('Tmux 会话未初始化');
    }

    const sessionName = this.currentSessionName;

    return new Promise((resolve, reject) => {
      const checkInterval = setInterval(async () => {
        try {
          const output = await this.tmux.captureOutput(sessionName);

          // 检查 WorkerRunner 完成标志
          if (output.includes('Task completed successfully')) {
            clearInterval(checkInterval);
            resolve({
              success: true,
              output: 'Task completed via WorkerRunner',
              duration: Date.now() - startTime,
              metadata: {
                executor: 'worker-runner',
                sessionName
              }
            });
            return;
          }

          // 检查失败标志
          if (output.includes('Task failed:') || output.includes('Fatal error:')) {
            clearInterval(checkInterval);
            const errorMatch = output.match(/(?:Task failed|Fatal error): (.+)/);
            const errorMsg = errorMatch ? errorMatch[1] : 'Unknown error';
            resolve({
              success: false,
              error: errorMsg,
              duration: Date.now() - startTime,
              metadata: {
                executor: 'worker-runner',
                sessionName
              }
            });
            return;
          }

          // 检查进程是否结束（WorkerRunner finished）
          if (output.includes('Worker') && output.includes('finished')) {
            clearInterval(checkInterval);
            // 检查最后的状态
            const isSuccess = !output.includes('failed') && !output.includes('error');
            resolve({
              success: isSuccess,
              output: isSuccess ? 'Task completed' : 'Task finished with issues',
              duration: Date.now() - startTime,
              metadata: {
                executor: 'worker-runner',
                sessionName
              }
            });
            return;
          }

          // 超时检查
          if (Date.now() - startTime > this.config.timeout) {
            clearInterval(checkInterval);
            reject(new Error(`任务 ${taskId} 执行超时 (${this.config.timeout}ms)`));
          }
        } catch (error) {
          clearInterval(checkInterval);
          reject(error);
        }
      }, this.config.monitorInterval);
    });
  }
}
