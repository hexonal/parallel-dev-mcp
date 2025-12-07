/**
 * 任务执行器
 * @module parallel/worker/TaskExecutor
 *
 * 在 Tmux 会话中执行 Claude Headless 命令
 * 监控输出并解析 stream-json 结果
 */

import { Task, TaskResult } from '../types';
import { TmuxController } from '../tmux/TmuxController';
import { SessionMonitor } from '../tmux/SessionMonitor';

/** stream-json 事件类型 */
interface StreamJsonEvent {
  type: string;
  result?: string;
  error?: string;
  message?: string;
  [key: string]: unknown;
}

/** 执行器配置 */
export interface TaskExecutorConfig {
  /** 检查间隔（毫秒） */
  checkInterval: number;
  /** 超时时间（毫秒） */
  timeout: number;
  /** 允许的工具 */
  allowedTools: string[];
  /** 权限模式 */
  permissionMode: 'acceptEdits' | 'bypassPermissions' | 'default';
}

/** 默认配置 */
const DEFAULT_CONFIG: TaskExecutorConfig = {
  checkInterval: 1000,
  timeout: 600000,
  allowedTools: ['Read', 'Edit', 'Write', 'Bash', 'Grep', 'Glob'],
  permissionMode: 'acceptEdits'
};

/**
 * TaskExecutor 在 Tmux 中执行 Claude Headless 任务
 */
export class TaskExecutor {
  private tmux: TmuxController;
  private monitor: SessionMonitor;
  private tmuxSession: string;
  private config: TaskExecutorConfig;

  /**
   * 创建 TaskExecutor
   * @param tmux TmuxController 实例
   * @param monitor SessionMonitor 实例
   * @param tmuxSession Tmux 会话名称
   * @param config 执行器配置
   */
  constructor(
    tmux: TmuxController,
    monitor: SessionMonitor,
    tmuxSession: string,
    config: Partial<TaskExecutorConfig> = {}
  ) {
    this.tmux = tmux;
    this.monitor = monitor;
    this.tmuxSession = tmuxSession;
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * 执行任务
   * @param task 任务对象
   * @param worktreePath Worktree 路径
   * @returns 任务执行结果
   */
  async execute(task: Task, worktreePath: string): Promise<TaskResult> {
    const startTime = Date.now();

    try {
      // 1. 构建任务 Prompt
      const prompt = this.buildTaskPrompt(task);

      // 2. 构建 Claude Headless 命令
      const claudeCommand = this.buildClaudeCommand(prompt, worktreePath);

      // 3. 在 Tmux 中执行
      await this.tmux.sendCommand(this.tmuxSession, claudeCommand);

      // 4. 监控输出并等待完成
      const result = await this.waitForCompletion(task.id);

      // 5. 计算执行时长
      result.duration = Date.now() - startTime;

      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
        duration: Date.now() - startTime
      };
    }
  }

  /**
   * 构建任务 Prompt
   * @param task 任务对象
   * @returns 格式化的 Prompt
   */
  private buildTaskPrompt(task: Task): string {
    return `
你是 ParallelDev Worker，正在执行任务。

## 任务信息
- ID: ${task.id}
- 标题: ${task.title}
- 描述: ${task.description}
${task.estimatedHours ? `- 预估工时: ${task.estimatedHours} 小时` : ''}

## 执行要求
1. 完成任务描述中的所有需求
2. 遵循项目代码规范
3. 编写必要的测试（如适用）
4. 确保代码质量（无 lint 错误）
5. 任务完成后输出 "TASK_COMPLETED"
6. 如遇到无法解决的问题，输出 "TASK_FAILED: <原因>"

## 注意事项
- 不要修改不相关的文件
- 保持代码简洁，遵循 YAGNI 原则
- 如有疑问，优先选择简单方案

开始执行任务。
    `.trim();
  }

  /**
   * 构建 Claude Headless 命令
   * @param prompt 任务 Prompt
   * @param worktreePath 工作目录
   * @returns 完整的命令字符串
   */
  private buildClaudeCommand(prompt: string, worktreePath: string): string {
    // 转义 Prompt 中的特殊字符
    const escapedPrompt = this.escapeForShell(prompt);

    const args = [
      'claude',
      '-p', `"${escapedPrompt}"`,
      '--output-format', 'stream-json',
      '--permission-mode', this.config.permissionMode,
      '--allowedTools', this.config.allowedTools.join(','),
      '--cwd', `"${worktreePath}"`
    ];

    return args.join(' ');
  }

  /**
   * 转义 Shell 特殊字符
   * @param str 原始字符串
   * @returns 转义后的字符串
   */
  private escapeForShell(str: string): string {
    return str
      .replace(/\\/g, '\\\\')
      .replace(/"/g, '\\"')
      .replace(/\$/g, '\\$')
      .replace(/`/g, '\\`')
      .replace(/\n/g, '\\n');
  }

  /**
   * 等待任务完成
   * @param taskId 任务 ID（用于日志）
   * @returns 任务执行结果
   */
  private async waitForCompletion(taskId: string): Promise<TaskResult> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      let lastOutput = '';
      let checkCount = 0;

      const checkCompletion = async () => {
        checkCount++;

        // 检查超时
        if (Date.now() - startTime > this.config.timeout) {
          reject(new Error(`任务 ${taskId} 执行超时`));
          return;
        }

        try {
          // 捕获 Tmux 输出
          const output = await this.tmux.captureOutput(this.tmuxSession);

          // 只处理新输出
          const newOutput = output.slice(lastOutput.length);
          lastOutput = output;

          if (newOutput) {
            // 解析 stream-json 事件
            const events = this.parseStreamJson(newOutput);

            for (const event of events) {
              // 检测完成事件
              if (event.type === 'result') {
                resolve({
                  success: true,
                  output: event.result || output
                });
                return;
              }

              // 检测错误事件
              if (event.type === 'error') {
                resolve({
                  success: false,
                  error: event.error || 'Unknown error'
                });
                return;
              }
            }

            // 检测自定义完成标记
            if (this.detectCompletion(newOutput)) {
              resolve({
                success: true,
                output: output
              });
              return;
            }

            // 检测自定义失败标记
            const errorMessage = this.detectFailure(newOutput);
            if (errorMessage) {
              resolve({
                success: false,
                error: errorMessage
              });
              return;
            }
          }

          // 继续检查
          setTimeout(checkCompletion, this.config.checkInterval);
        } catch (error) {
          // Tmux 会话可能已断开
          reject(new Error(`监控任务 ${taskId} 失败: ${error}`));
        }
      };

      // 开始检查
      checkCompletion();
    });
  }

  /**
   * 解析 stream-json 输出
   * @param output 原始输出
   * @returns 解析后的事件数组
   */
  private parseStreamJson(output: string): StreamJsonEvent[] {
    const events: StreamJsonEvent[] = [];
    const lines = output.split('\n');

    for (const line of lines) {
      const trimmedLine = line.trim();

      // 跳过空行
      if (!trimmedLine) continue;

      // 尝试解析 JSON
      if (trimmedLine.startsWith('{') && trimmedLine.endsWith('}')) {
        try {
          const event = JSON.parse(trimmedLine) as StreamJsonEvent;
          events.push(event);
        } catch {
          // 不是有效 JSON，忽略
        }
      }
    }

    return events;
  }

  /**
   * 检测任务完成标记
   * @param content 输出内容
   * @returns 是否完成
   */
  private detectCompletion(content: string): boolean {
    const completionMarkers = [
      '"type":"result"',
      'TASK_COMPLETED',
      '✅ Task completed',
      '任务完成'
    ];

    return completionMarkers.some(marker => content.includes(marker));
  }

  /**
   * 检测任务失败标记
   * @param content 输出内容
   * @returns 错误信息或 null
   */
  private detectFailure(content: string): string | null {
    // 检测 TASK_FAILED 标记
    const failedMatch = content.match(/TASK_FAILED:\s*(.+)/);
    if (failedMatch) {
      return failedMatch[1].trim();
    }

    // 检测 stream-json error 事件
    if (content.includes('"type":"error"')) {
      const errorMatch = content.match(/"error":"([^"]+)"/);
      return errorMatch ? errorMatch[1] : 'Unknown error';
    }

    return null;
  }

  /**
   * 取消正在执行的任务
   */
  async cancel(): Promise<void> {
    await this.tmux.sendInterrupt(this.tmuxSession);
  }

  /**
   * 获取当前输出
   * @returns 当前 Tmux 会话输出
   */
  async getCurrentOutput(): Promise<string> {
    return this.tmux.captureOutput(this.tmuxSession);
  }

  /**
   * 设置超时时间
   * @param timeoutMs 超时毫秒数
   */
  setTimeout(timeoutMs: number): void {
    this.config.timeout = timeoutMs;
  }

  /**
   * 设置检查间隔
   * @param intervalMs 间隔毫秒数
   */
  setCheckInterval(intervalMs: number): void {
    this.config.checkInterval = intervalMs;
  }
}
