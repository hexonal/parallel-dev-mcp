/**
 * Git Worktree 管理器
 * @module parallel/git/WorktreeManager
 *
 * 负责创建、删除和管理 Git Worktree
 * 每个 Worker 使用独立的 Worktree 进行隔离开发
 */

import { execSync } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

/** Worktree 信息 */
export interface WorktreeInfo {
  /** Worktree 路径 */
  path: string;
  /** 分支名称 */
  branch: string;
  /** 关联的任务 ID */
  taskId: string;
  /** 创建时间 */
  createdAt: string;
}

/**
 * WorktreeManager 管理 Git Worktree 的生命周期
 */
export class WorktreeManager {
  private projectRoot: string;
  private worktreeDir: string;

  /**
   * 创建 WorktreeManager
   * @param projectRoot 项目根目录
   * @param worktreeDir Worktree 目录名（默认 .worktrees）
   */
  constructor(projectRoot: string, worktreeDir: string = '.worktrees') {
    this.projectRoot = projectRoot;
    this.worktreeDir = path.join(projectRoot, worktreeDir);
  }

  /**
   * 创建 Worktree
   * @param taskId 任务 ID
   * @param baseBranch 基础分支（默认 main）
   * @returns Worktree 信息
   */
  async create(
    taskId: string,
    baseBranch: string = 'main'
  ): Promise<WorktreeInfo> {
    const worktreePath = path.join(this.worktreeDir, `task-${taskId}`);
    const branchName = `task/${taskId}`;

    // 确保 worktree 目录存在
    if (!fs.existsSync(this.worktreeDir)) {
      fs.mkdirSync(this.worktreeDir, { recursive: true });
    }

    // 检查 worktree 是否已存在
    if (fs.existsSync(worktreePath)) {
      throw new Error(`Worktree 已存在: ${worktreePath}`);
    }

    try {
      // 创建新的 worktree 和分支
      execSync(
        `git worktree add "${worktreePath}" -b "${branchName}" "${baseBranch}"`,
        {
          cwd: this.projectRoot,
          stdio: 'pipe'
        }
      );

      return {
        path: worktreePath,
        branch: branchName,
        taskId,
        createdAt: new Date().toISOString()
      };
    } catch (error) {
      // 尝试清理失败的 worktree
      this.forceRemove(taskId);
      throw new Error(`创建 Worktree 失败: ${error}`);
    }
  }

  /**
   * 删除 Worktree
   * @param taskId 任务 ID
   */
  async remove(taskId: string): Promise<void> {
    const worktreePath = path.join(this.worktreeDir, `task-${taskId}`);

    if (!fs.existsSync(worktreePath)) {
      return;
    }

    try {
      execSync(`git worktree remove "${worktreePath}" --force`, {
        cwd: this.projectRoot,
        stdio: 'pipe'
      });
    } catch (error) {
      // 如果 git worktree remove 失败，尝试手动清理
      this.forceRemove(taskId);
    }
  }

  /**
   * 强制删除 Worktree（手动清理）
   * @param taskId 任务 ID
   */
  private forceRemove(taskId: string): void {
    const worktreePath = path.join(this.worktreeDir, `task-${taskId}`);

    if (fs.existsSync(worktreePath)) {
      fs.rmSync(worktreePath, { recursive: true, force: true });
    }

    // 清理 git worktree 引用
    try {
      execSync('git worktree prune', {
        cwd: this.projectRoot,
        stdio: 'pipe'
      });
    } catch {
      // 忽略清理错误
    }
  }

  /**
   * 列出所有 Worktree
   * @returns Worktree 信息数组
   */
  list(): WorktreeInfo[] {
    const results: WorktreeInfo[] = [];

    try {
      const output = execSync('git worktree list --porcelain', {
        cwd: this.projectRoot,
        encoding: 'utf-8'
      });

      const blocks = output.trim().split('\n\n');

      for (const block of blocks) {
        const lines = block.split('\n');
        const worktreeLine = lines.find(l => l.startsWith('worktree '));
        const branchLine = lines.find(l => l.startsWith('branch '));

        if (worktreeLine && branchLine) {
          const wtPath = worktreeLine.replace('worktree ', '');
          const branch = branchLine.replace('branch refs/heads/', '');

          // 只返回我们管理的 worktree
          if (wtPath.includes(this.worktreeDir)) {
            const taskId = this.extractTaskId(wtPath);
            if (taskId) {
              results.push({
                path: wtPath,
                branch,
                taskId,
                createdAt: ''
              });
            }
          }
        }
      }
    } catch {
      // 如果 git 命令失败，返回空数组
    }

    return results;
  }

  /**
   * 从路径提取任务 ID
   * @param wtPath Worktree 路径
   * @returns 任务 ID 或 null
   */
  private extractTaskId(wtPath: string): string | null {
    const match = wtPath.match(/task-([^/]+)$/);
    return match ? match[1] : null;
  }

  /**
   * 检查 Worktree 是否存在
   * @param taskId 任务 ID
   * @returns 是否存在
   */
  exists(taskId: string): boolean {
    const worktreePath = path.join(this.worktreeDir, `task-${taskId}`);
    return fs.existsSync(worktreePath);
  }

  /**
   * 获取 Worktree 路径
   * @param taskId 任务 ID
   * @returns Worktree 路径
   */
  getPath(taskId: string): string {
    return path.join(this.worktreeDir, `task-${taskId}`);
  }

  /**
   * 清理所有 Worktree
   */
  async cleanup(): Promise<void> {
    const worktrees = this.list();

    for (const wt of worktrees) {
      await this.remove(wt.taskId);
    }

    // 删除空的 worktree 目录
    if (fs.existsSync(this.worktreeDir)) {
      const remaining = fs.readdirSync(this.worktreeDir);
      if (remaining.length === 0) {
        fs.rmdirSync(this.worktreeDir);
      }
    }
  }

  /**
   * 在 Worktree 中执行 Git 命令
   * @param taskId 任务 ID
   * @param command Git 命令
   * @returns 命令输出
   */
  execGitCommand(taskId: string, command: string): string {
    const worktreePath = this.getPath(taskId);

    if (!fs.existsSync(worktreePath)) {
      throw new Error(`Worktree 不存在: ${worktreePath}`);
    }

    return execSync(`git ${command}`, {
      cwd: worktreePath,
      encoding: 'utf-8'
    });
  }

  /**
   * 提交 Worktree 中的更改
   * @param taskId 任务 ID
   * @param message 提交信息
   */
  async commit(taskId: string, message: string): Promise<void> {
    const worktreePath = this.getPath(taskId);

    execSync('git add -A', { cwd: worktreePath, stdio: 'pipe' });
    execSync(`git commit -m "${message}"`, {
      cwd: worktreePath,
      stdio: 'pipe'
    });
  }

  /**
   * 将 Worktree 分支推送到远程
   * @param taskId 任务 ID
   */
  async push(taskId: string): Promise<void> {
    const branchName = `task/${taskId}`;

    execSync(`git push -u origin "${branchName}"`, {
      cwd: this.getPath(taskId),
      stdio: 'pipe'
    });
  }
}
