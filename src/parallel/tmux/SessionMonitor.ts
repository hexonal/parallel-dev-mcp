/**
 * Tmux 会话监控器
 * @module parallel/tmux/SessionMonitor
 *
 * 监控 Tmux 会话输出，检测任务完成状态
 */

import { EventEmitter } from 'events';
import { TmuxController } from './TmuxController';

/** 会话监控事件类型 */
export interface SessionMonitorEvents {
  /** 新输出事件 */
  output: (data: { sessionName: string; content: string }) => void;
  /** 任务完成事件 */
  completed: (data: { sessionName: string; output: string }) => void;
  /** 任务失败事件 */
  failed: (data: { sessionName: string; error: string }) => void;
  /** 会话断开事件 */
  disconnected: (sessionName: string) => void;
}

/**
 * SessionMonitor 监控 Tmux 会话输出
 */
export class SessionMonitor extends EventEmitter {
  private tmux: TmuxController;
  private sessions: Map<string, NodeJS.Timeout> = new Map();
  private lastOutput: Map<string, string> = new Map();
  private checkInterval: number;

  /**
   * 创建 SessionMonitor
   * @param tmux TmuxController 实例
   * @param checkInterval 检查间隔（毫秒，默认 1000）
   */
  constructor(tmux: TmuxController, checkInterval: number = 1000) {
    super();
    this.tmux = tmux;
    this.checkInterval = checkInterval;
  }

  /**
   * 开始监控会话
   * @param sessionName 会话名称
   */
  startMonitoring(sessionName: string): void {
    if (this.sessions.has(sessionName)) {
      return;
    }

    this.lastOutput.set(sessionName, '');

    const timer = setInterval(async () => {
      await this.checkSession(sessionName);
    }, this.checkInterval);

    this.sessions.set(sessionName, timer);
  }

  /**
   * 检查会话状态和输出
   * @param sessionName 会话名称
   */
  private async checkSession(sessionName: string): Promise<void> {
    // 检查会话是否还存在
    if (!this.tmux.sessionExists(sessionName)) {
      this.stopMonitoring(sessionName);
      this.emit('disconnected', sessionName);
      return;
    }

    try {
      const output = await this.tmux.captureOutput(sessionName);
      const lastOutput = this.lastOutput.get(sessionName) || '';

      // 检查是否有新输出
      if (output !== lastOutput) {
        const newContent = this.extractNewContent(lastOutput, output);

        if (newContent) {
          this.emit('output', { sessionName, content: newContent });

          // 检测任务完成标记
          if (this.detectCompletion(newContent)) {
            this.emit('completed', { sessionName, output });
          }

          // 检测错误标记
          const error = this.detectError(newContent);
          if (error) {
            this.emit('failed', { sessionName, error });
          }
        }

        this.lastOutput.set(sessionName, output);
      }
    } catch (error) {
      // 会话可能已被销毁
      this.stopMonitoring(sessionName);
      this.emit('disconnected', sessionName);
    }
  }

  /**
   * 提取新输出内容
   * @param lastOutput 上次输出
   * @param currentOutput 当前输出
   * @returns 新增内容
   */
  private extractNewContent(
    lastOutput: string,
    currentOutput: string
  ): string {
    if (currentOutput.startsWith(lastOutput)) {
      return currentOutput.slice(lastOutput.length);
    }

    // 如果不是简单追加，返回整个新输出
    return currentOutput;
  }

  /**
   * 检测任务完成
   * @param content 输出内容
   * @returns 是否完成
   */
  private detectCompletion(content: string): boolean {
    // 检测 Claude stream-json 的 result 事件
    const completionMarkers = [
      '"type":"result"',
      'TASK_COMPLETED',
      '✅ Task completed'
    ];

    return completionMarkers.some(marker => content.includes(marker));
  }

  /**
   * 检测错误
   * @param content 输出内容
   * @returns 错误信息或 null
   */
  private detectError(content: string): string | null {
    // 检测 Claude stream-json 的 error 事件
    if (content.includes('"type":"error"')) {
      const match = content.match(/"error":"([^"]+)"/);
      return match ? match[1] : 'Unknown error';
    }

    // 检测常见错误标记
    const errorMarkers = ['Error:', 'error:', 'FATAL:', 'TASK_FAILED'];
    for (const marker of errorMarkers) {
      const index = content.indexOf(marker);
      if (index !== -1) {
        // 提取错误消息
        const errorLine = content.slice(index).split('\n')[0];
        return errorLine;
      }
    }

    return null;
  }

  /**
   * 停止监控会话
   * @param sessionName 会话名称
   */
  stopMonitoring(sessionName: string): void {
    const timer = this.sessions.get(sessionName);

    if (timer) {
      clearInterval(timer);
      this.sessions.delete(sessionName);
      this.lastOutput.delete(sessionName);
    }
  }

  /**
   * 停止所有监控
   */
  stopAll(): void {
    for (const sessionName of this.sessions.keys()) {
      this.stopMonitoring(sessionName);
    }
  }

  /**
   * 获取正在监控的会话列表
   * @returns 会话名称数组
   */
  getMonitoredSessions(): string[] {
    return Array.from(this.sessions.keys());
  }

  /**
   * 检查是否正在监控指定会话
   * @param sessionName 会话名称
   * @returns 是否正在监控
   */
  isMonitoring(sessionName: string): boolean {
    return this.sessions.has(sessionName);
  }

  /**
   * 设置检查间隔
   * @param intervalMs 间隔毫秒数
   */
  setCheckInterval(intervalMs: number): void {
    this.checkInterval = intervalMs;
  }
}
