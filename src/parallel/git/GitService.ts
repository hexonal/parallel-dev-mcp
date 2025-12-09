/**
 * Git 服务 - 统一的 Git 操作接口
 * @module parallel/git/GitService
 *
 * 整合 Worktree 管理 + 通用 Git 操作
 * 基于 simple-git 库实现
 */

import path from 'path';
import fs from 'fs';
import { type SimpleGit, type StatusResult, simpleGit } from 'simple-git';

// ============================================
// 类型定义
// ============================================

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

/** Git 状态摘要 */
export interface GitStatusSummary {
  isClean: boolean;
  staged: number;
  modified: number;
  deleted: number;
  untracked: number;
  totalChanges: number;
  currentBranch: string;
}

/** 提交选项 */
export interface CommitOptions {
  /** 元数据 */
  metadata?: Record<string, string>;
  /** 允许空提交 */
  allowEmpty?: boolean;
  /** 禁止在默认分支提交 */
  enforceNonDefaultBranch?: boolean;
  /** 强制提交 */
  force?: boolean;
}

/** 提交信息 */
export interface CommitInfo {
  hash: string;
  date: string;
  message: string;
  authorName: string;
  authorEmail: string;
}

// ============================================
// GitService 实现
// ============================================

/**
 * GitService - 统一的 Git 操作服务
 *
 * 功能：
 * - 仓库状态检查
 * - 分支管理
 * - Worktree 管理
 * - 提交操作
 */
export class GitService {
  private projectRoot: string;
  private worktreeDir: string;
  private git: SimpleGit;

  /**
   * 创建 GitService
   * @param projectRoot 项目根目录（必须是绝对路径）
   * @param worktreeDir Worktree 目录名（默认 .worktrees）
   */
  constructor(projectRoot: string, worktreeDir: string = '.worktrees') {
    if (!projectRoot) {
      throw new Error('Project path is required');
    }

    if (!path.isAbsolute(projectRoot)) {
      throw new Error('Project path must be an absolute path');
    }

    this.projectRoot = path.normalize(projectRoot);
    this.worktreeDir = path.join(this.projectRoot, worktreeDir);
    this.git = simpleGit(this.projectRoot);
  }

  // ============================================
  // 仓库验证
  // ============================================

  /**
   * 检查是否为 Git 仓库
   */
  async isGitRepository(): Promise<boolean> {
    try {
      const gitPath = path.join(this.projectRoot, '.git');
      if (fs.existsSync(gitPath)) {
        return true;
      }
      await this.git.revparse(['--git-dir']);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * 确保在有效的 Git 仓库中
   */
  async ensureGitRepository(): Promise<void> {
    const isRepo = await this.isGitRepository();
    if (!isRepo) {
      throw new Error(
        `不是 Git 仓库: ${this.projectRoot}\n` +
        `请在 Git 仓库中运行此命令，或使用 'git init' 初始化。`
      );
    }
  }

  /**
   * 获取仓库根路径
   */
  async getRepositoryRoot(): Promise<string> {
    const result = await this.git.revparse(['--show-toplevel']);
    return path.normalize(result.trim());
  }

  // ============================================
  // 工作树状态
  // ============================================

  /**
   * 检查工作树是否干净
   */
  async isWorkingTreeClean(): Promise<boolean> {
    const status = await this.git.status();
    return status.isClean();
  }

  /**
   * 获取 Git 状态
   */
  async getStatus(): Promise<StatusResult> {
    return this.git.status();
  }

  /**
   * 获取状态摘要
   */
  async getStatusSummary(): Promise<GitStatusSummary> {
    const status = await this.git.status();
    return {
      isClean: status.isClean(),
      staged: status.staged.length,
      modified: status.modified.length,
      deleted: status.deleted.length,
      untracked: status.not_added.length,
      totalChanges: status.staged.length + status.modified.length +
                    status.deleted.length + status.not_added.length,
      currentBranch: status.current || 'HEAD'
    };
  }

  /**
   * 确保工作树干净
   */
  async ensureCleanWorkingTree(): Promise<void> {
    const summary = await this.getStatusSummary();
    if (!summary.isClean) {
      throw new Error(
        `工作树不干净: ${this.projectRoot}\n` +
        `暂存: ${summary.staged}, 修改: ${summary.modified}, ` +
        `删除: ${summary.deleted}, 未跟踪: ${summary.untracked}\n` +
        `请提交或暂存更改后再继续。`
      );
    }
  }

  // ============================================
  // 分支操作
  // ============================================

  /**
   * 获取当前分支名
   */
  async getCurrentBranch(): Promise<string> {
    const status = await this.git.status();
    return status.current || 'HEAD';
  }

  /**
   * 列出所有本地分支
   */
  async listBranches(): Promise<string[]> {
    const branchSummary = await this.git.branchLocal();
    return Object.keys(branchSummary.branches);
  }

  /**
   * 检查分支是否存在
   */
  async branchExists(branchName: string): Promise<boolean> {
    const branches = await this.listBranches();
    return branches.includes(branchName);
  }

  /**
   * 创建新分支
   */
  async createBranch(branchName: string, checkout: boolean = false): Promise<void> {
    const exists = await this.branchExists(branchName);
    if (exists) {
      throw new Error(`分支已存在: ${branchName}`);
    }

    if (checkout) {
      await this.ensureCleanWorkingTree();
      await this.git.checkoutLocalBranch(branchName);
    } else {
      await this.git.branch([branchName]);
    }
  }

  /**
   * 切换分支
   */
  async checkoutBranch(branchName: string, force: boolean = false): Promise<void> {
    const exists = await this.branchExists(branchName);
    if (!exists) {
      throw new Error(`分支不存在: ${branchName}`);
    }

    if (!force) {
      await this.ensureCleanWorkingTree();
    }

    const options = force ? ['-f', branchName] : [branchName];
    await this.git.checkout(options);
  }

  /**
   * 删除分支
   */
  async deleteBranch(branchName: string, force: boolean = false): Promise<void> {
    const exists = await this.branchExists(branchName);
    if (!exists) {
      throw new Error(`分支不存在: ${branchName}`);
    }

    const current = await this.getCurrentBranch();
    if (current === branchName) {
      throw new Error(`无法删除当前分支: ${branchName}`);
    }

    const options = force ? ['-D', branchName] : ['-d', branchName];
    await this.git.branch(options);
  }

  /**
   * 获取默认分支名
   */
  async getDefaultBranch(): Promise<string> {
    const branches = await this.listBranches();
    const defaultBranches = ['main', 'master', 'develop'];

    for (const branch of defaultBranches) {
      if (branches.includes(branch)) {
        return branch;
      }
    }
    return 'main';
  }

  // ============================================
  // Worktree 管理
  // ============================================

  /**
   * 创建 Worktree
   * @param taskId 任务 ID
   * @param baseBranch 基础分支（默认 main）
   */
  async createWorktree(taskId: string, baseBranch?: string): Promise<WorktreeInfo> {
    const base = baseBranch || await this.getDefaultBranch();
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
      await this.git.raw(['worktree', 'add', worktreePath, '-b', branchName, base]);

      return {
        path: worktreePath,
        branch: branchName,
        taskId,
        createdAt: new Date().toISOString()
      };
    } catch (error) {
      // 清理失败的 worktree
      this.forceRemoveWorktree(taskId);
      throw new Error(`创建 Worktree 失败: ${error}`);
    }
  }

  /**
   * 删除 Worktree
   */
  async removeWorktree(taskId: string): Promise<void> {
    const worktreePath = path.join(this.worktreeDir, `task-${taskId}`);

    if (!fs.existsSync(worktreePath)) {
      return;
    }

    try {
      await this.git.raw(['worktree', 'remove', worktreePath, '--force']);
    } catch {
      this.forceRemoveWorktree(taskId);
    }
  }

  /**
   * 强制删除 Worktree（手动清理）
   */
  private forceRemoveWorktree(taskId: string): void {
    const worktreePath = path.join(this.worktreeDir, `task-${taskId}`);

    if (fs.existsSync(worktreePath)) {
      fs.rmSync(worktreePath, { recursive: true, force: true });
    }

    try {
      this.git.raw(['worktree', 'prune']);
    } catch {
      // 忽略清理错误
    }
  }

  /**
   * 列出所有 Worktree
   */
  async listWorktrees(): Promise<WorktreeInfo[]> {
    const results: WorktreeInfo[] = [];

    try {
      const output = await this.git.raw(['worktree', 'list', '--porcelain']);
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
            const taskId = this.extractTaskIdFromPath(wtPath);
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
      // 返回空数组
    }

    return results;
  }

  /**
   * 检查 Worktree 是否存在
   */
  worktreeExists(taskId: string): boolean {
    const worktreePath = path.join(this.worktreeDir, `task-${taskId}`);
    return fs.existsSync(worktreePath);
  }

  /**
   * 获取 Worktree 路径
   */
  getWorktreePath(taskId: string): string {
    return path.join(this.worktreeDir, `task-${taskId}`);
  }

  /**
   * 清理所有 Worktree
   */
  async cleanupAllWorktrees(): Promise<void> {
    const worktrees = await this.listWorktrees();

    for (const wt of worktrees) {
      await this.removeWorktree(wt.taskId);
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
   * 从路径提取任务 ID
   */
  private extractTaskIdFromPath(wtPath: string): string | null {
    const match = wtPath.match(/task-([^/]+)$/);
    return match ? match[1] : null;
  }

  // ============================================
  // Worktree 内操作
  // ============================================

  /**
   * 在 Worktree 中执行 Git 命令
   */
  async execInWorktree(taskId: string, ...args: string[]): Promise<string> {
    const worktreePath = this.getWorktreePath(taskId);

    if (!fs.existsSync(worktreePath)) {
      throw new Error(`Worktree 不存在: ${worktreePath}`);
    }

    const worktreeGit = simpleGit(worktreePath);
    return worktreeGit.raw(args);
  }

  /**
   * 在 Worktree 中提交更改
   */
  async commitInWorktree(taskId: string, message: string): Promise<void> {
    const worktreePath = this.getWorktreePath(taskId);
    const worktreeGit = simpleGit(worktreePath);

    await worktreeGit.add('-A');
    await worktreeGit.commit(message);
  }

  /**
   * 推送 Worktree 分支到远程
   */
  async pushWorktree(taskId: string): Promise<void> {
    const branchName = `task/${taskId}`;
    const worktreePath = this.getWorktreePath(taskId);
    const worktreeGit = simpleGit(worktreePath);

    await worktreeGit.push(['-u', 'origin', branchName]);
  }

  // ============================================
  // 提交操作
  // ============================================

  /**
   * 暂存文件
   */
  async stageFiles(files: string[]): Promise<void> {
    await this.git.add(files);
  }

  /**
   * 暂存所有文件
   */
  async stageAll(): Promise<void> {
    await this.git.add('-A');
  }

  /**
   * 取消暂存
   */
  async unstageFiles(files: string[]): Promise<void> {
    await this.git.reset(['HEAD', '--', ...files]);
  }

  /**
   * 创建提交
   */
  async commit(message: string, options: CommitOptions = {}): Promise<void> {
    if (options.enforceNonDefaultBranch && !options.force) {
      const currentBranch = await this.getCurrentBranch();
      const defaultBranch = await this.getDefaultBranch();
      if (currentBranch === defaultBranch) {
        throw new Error(
          `无法在默认分支提交: ${currentBranch}\n` +
          `请创建功能分支或使用 force 选项。`
        );
      }
    }

    const status = await this.git.status();
    if (!options.allowEmpty && status.staged.length === 0) {
      throw new Error('没有暂存的更改可提交');
    }

    const commitArgs: string[] = ['-m', message];

    if (options.metadata) {
      for (const [key, value] of Object.entries(options.metadata)) {
        commitArgs.push('-m', `[${key}:${value}]`);
      }
    }

    commitArgs.push('--no-gpg-sign');
    if (options.allowEmpty) {
      commitArgs.push('--allow-empty');
    }

    await this.git.commit(commitArgs);
  }

  /**
   * 获取提交日志
   */
  async getCommitLog(maxCount: number = 10): Promise<CommitInfo[]> {
    const log = await this.git.log({
      maxCount,
      format: {
        hash: '%H',
        date: '%ai',
        message: '%B',
        author_name: '%an',
        author_email: '%ae'
      }
    });

    return log.all.map(entry => ({
      hash: entry.hash,
      date: entry.date,
      message: entry.message,
      authorName: entry.author_name,
      authorEmail: entry.author_email
    }));
  }

  /**
   * 获取最后一次提交
   */
  async getLastCommit(): Promise<CommitInfo | null> {
    const commits = await this.getCommitLog(1);
    return commits[0] || null;
  }

  // ============================================
  // 远程操作
  // ============================================

  /**
   * 检查是否有远程仓库
   */
  async hasRemote(): Promise<boolean> {
    const remotes = await this.git.getRemotes();
    return remotes.length > 0;
  }

  /**
   * 获取所有远程仓库
   */
  async getRemotes(): Promise<{ name: string; refs: { fetch: string; push: string } }[]> {
    return this.git.getRemotes(true);
  }

  /**
   * 推送到远程
   */
  async push(remote: string = 'origin', branch?: string): Promise<void> {
    const currentBranch = branch || await this.getCurrentBranch();
    await this.git.push(remote, currentBranch);
  }

  /**
   * 拉取远程更新
   */
  async pull(remote: string = 'origin', branch?: string): Promise<void> {
    const currentBranch = branch || await this.getCurrentBranch();
    await this.git.pull(remote, currentBranch);
  }
}
