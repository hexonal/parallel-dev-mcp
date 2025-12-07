/**
 * Tmux 会话控制器
 * @module parallel/tmux/TmuxController
 *
 * 管理 Tmux 会话的创建、销毁和命令执行
 * 每个 Worker 运行在独立的 Tmux 会话中
 */

import { execSync } from 'child_process';

/**
 * TmuxController 管理 Tmux 会话
 */
export class TmuxController {
  private sessionPrefix: string;

  /**
   * 创建 TmuxController
   * @param sessionPrefix 会话名称前缀（默认 parallel-dev）
   */
  constructor(sessionPrefix: string = 'parallel-dev') {
    this.sessionPrefix = sessionPrefix;
  }

  /**
   * 创建新的 Tmux 会话
   * @param sessionId 会话 ID
   * @param workingDir 工作目录
   * @returns 完整会话名称
   */
  async createSession(
    sessionId: string,
    workingDir: string
  ): Promise<string> {
    const sessionName = `${this.sessionPrefix}-${sessionId}`;

    // 检查会话是否已存在
    if (this.sessionExists(sessionName)) {
      throw new Error(`Tmux 会话已存在: ${sessionName}`);
    }

    try {
      execSync(
        `tmux new-session -d -s "${sessionName}" -c "${workingDir}"`,
        { stdio: 'pipe' }
      );

      return sessionName;
    } catch (error) {
      throw new Error(`创建 Tmux 会话失败: ${error}`);
    }
  }

  /**
   * 杀死 Tmux 会话
   * @param sessionName 会话名称
   */
  async killSession(sessionName: string): Promise<void> {
    if (!this.sessionExists(sessionName)) {
      return;
    }

    try {
      execSync(`tmux kill-session -t "${sessionName}"`, { stdio: 'pipe' });
    } catch {
      // 忽略杀死会话失败的错误
    }
  }

  /**
   * 向会话发送命令
   * @param sessionName 会话名称
   * @param command 要执行的命令
   */
  async sendCommand(sessionName: string, command: string): Promise<void> {
    if (!this.sessionExists(sessionName)) {
      throw new Error(`Tmux 会话不存在: ${sessionName}`);
    }

    // 转义单引号
    const escapedCommand = command.replace(/'/g, "'\\''");

    try {
      execSync(
        `tmux send-keys -t "${sessionName}" '${escapedCommand}' Enter`,
        { stdio: 'pipe' }
      );
    } catch (error) {
      throw new Error(`发送命令失败: ${error}`);
    }
  }

  /**
   * 捕获会话输出
   * @param sessionName 会话名称
   * @param lines 捕获行数（默认 1000）
   * @returns 会话输出内容
   */
  async captureOutput(
    sessionName: string,
    lines: number = 1000
  ): Promise<string> {
    if (!this.sessionExists(sessionName)) {
      throw new Error(`Tmux 会话不存在: ${sessionName}`);
    }

    try {
      return execSync(
        `tmux capture-pane -t "${sessionName}" -p -S -${lines}`,
        { encoding: 'utf-8' }
      );
    } catch (error) {
      throw new Error(`捕获输出失败: ${error}`);
    }
  }

  /**
   * 列出所有管理的会话
   * @returns 会话名称数组
   */
  listSessions(): string[] {
    try {
      const output = execSync('tmux list-sessions -F "#{session_name}"', {
        encoding: 'utf-8'
      });

      return output
        .trim()
        .split('\n')
        .filter(s => s.startsWith(this.sessionPrefix));
    } catch {
      // 如果没有 tmux 会话或 tmux 未安装，返回空数组
      return [];
    }
  }

  /**
   * 检查会话是否存在
   * @param sessionName 会话名称
   * @returns 是否存在
   */
  sessionExists(sessionName: string): boolean {
    try {
      execSync(`tmux has-session -t "${sessionName}"`, { stdio: 'pipe' });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * 获取完整会话名称
   * @param sessionId 会话 ID
   * @returns 完整会话名称
   */
  getSessionName(sessionId: string): string {
    return `${this.sessionPrefix}-${sessionId}`;
  }

  /**
   * 杀死所有管理的会话
   */
  async killAllSessions(): Promise<void> {
    const sessions = this.listSessions();

    for (const session of sessions) {
      await this.killSession(session);
    }
  }

  /**
   * 发送 Ctrl+C 中断命令
   * @param sessionName 会话名称
   */
  async sendInterrupt(sessionName: string): Promise<void> {
    if (!this.sessionExists(sessionName)) {
      return;
    }

    try {
      execSync(`tmux send-keys -t "${sessionName}" C-c`, { stdio: 'pipe' });
    } catch {
      // 忽略错误
    }
  }

  /**
   * 清空会话历史
   * @param sessionName 会话名称
   */
  async clearHistory(sessionName: string): Promise<void> {
    if (!this.sessionExists(sessionName)) {
      return;
    }

    try {
      execSync(`tmux clear-history -t "${sessionName}"`, { stdio: 'pipe' });
    } catch {
      // 忽略错误
    }
  }

  /**
   * 检查 tmux 是否可用
   * @returns 是否可用
   */
  static isAvailable(): boolean {
    try {
      execSync('which tmux', { stdio: 'pipe' });
      return true;
    } catch {
      return false;
    }
  }
}
