/**
 * Tmux 会话控制器
 * @module parallel/tmux/TmuxController
 *
 * 管理 Tmux 会话的创建、销毁和命令执行
 * 每个 Worker 运行在独立的 Tmux 会话中
 *
 * 命名策略：
 * - 会话前缀：自动检测当前 tmux 会话名，或默认 'pdev'
 * - 会话 ID：worktree 名称
 * - 完整格式：{主会话名}-{worktree名}
 * - 示例：main-feature-auth, dev-bugfix-login
 */

import { execSync } from 'child_process';

/**
 * TmuxController 管理 Tmux 会话
 */
export class TmuxController {
  private sessionPrefix: string;

  /**
   * 创建 TmuxController
   * @param sessionPrefix 会话名称前缀（默认使用当前 Tmux 会话名）
   */
  constructor(sessionPrefix?: string) {
    // 如果没有指定前缀，尝试获取当前 Tmux 会话名作为前缀
    this.sessionPrefix = sessionPrefix || this.getCurrentTmuxSession() || 'pdev';
  }

  /**
   * 获取当前所在的 Tmux 会话名称
   * @returns 当前会话名称，如果不在 Tmux 中返回 null
   */
  private getCurrentTmuxSession(): string | null {
    // 方法 1: 检查 TMUX 环境变量
    if (process.env.TMUX) {
      try {
        const sessionName = execSync('tmux display-message -p "#{session_name}"', {
          encoding: 'utf-8'
        }).trim();
        if (sessionName) {
          return sessionName;
        }
      } catch {
        // 继续尝试其他方法
      }
    }

    // 方法 2: 检查 TMUX_PANE 环境变量并从 tmux 获取会话名
    if (process.env.TMUX_PANE) {
      try {
        const sessionName = execSync(
          `tmux display-message -t "${process.env.TMUX_PANE}" -p "#{session_name}"`,
          { encoding: 'utf-8' }
        ).trim();
        if (sessionName) {
          return sessionName;
        }
      } catch {
        // 继续尝试其他方法
      }
    }

    // 方法 3: 获取最近活跃的 attached 会话（用户可能从该会话运行命令）
    try {
      // 获取所有 attached 的会话
      const clients = execSync(
        'tmux list-clients -F "#{session_name}" 2>/dev/null | head -1',
        { encoding: 'utf-8' }
      ).trim();
      if (clients) {
        return clients;
      }
    } catch {
      // tmux 可能未运行或没有 attached 客户端
    }

    return null;
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
