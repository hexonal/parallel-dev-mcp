/**
 * Git Adapter
 * 爆改自 claude-task-master/packages/tm-core/src/modules/git/adapters/git-adapter.ts
 * 安全的 git 操作封装
 */

import path from 'path';
import fs from 'fs-extra';
import { type SimpleGit, type StatusResult, simpleGit } from 'simple-git';

/**
 * GitAdapter - 安全的 git 操作封装类
 */
export class GitAdapter {
  public projectPath: string;
  public git: SimpleGit;

  constructor(projectPath: string) {
    if (!projectPath) {
      throw new Error('Project path is required');
    }

    if (!path.isAbsolute(projectPath)) {
      throw new Error('Project path must be an absolute path');
    }

    this.projectPath = path.normalize(projectPath);
    this.git = simpleGit(this.projectPath);
  }

  /**
   * 检查是否为 git 仓库
   */
  async isGitRepository(): Promise<boolean> {
    try {
      const gitPath = path.join(this.projectPath, '.git');

      if (await fs.pathExists(gitPath)) {
        return true;
      }

      try {
        await this.git.revparse(['--git-dir']);
        return true;
      } catch {
        return false;
      }
    } catch {
      return false;
    }
  }

  /**
   * 确保在有效的 git 仓库中
   */
  async ensureGitRepository(): Promise<void> {
    const isRepo = await this.isGitRepository();
    if (!isRepo) {
      throw new Error(
        `not a git repository: ${this.projectPath}\n` +
          `Please run this command from within a git repository, or initialize one with 'git init'.`
      );
    }
  }

  /**
   * 获取仓库根路径
   */
  async getRepositoryRoot(): Promise<string> {
    try {
      const result = await this.git.revparse(['--show-toplevel']);
      return path.normalize(result.trim());
    } catch {
      throw new Error(`not a git repository: ${this.projectPath}`);
    }
  }

  /**
   * 检查工作树是否干净
   */
  async isWorkingTreeClean(): Promise<boolean> {
    const status = await this.git.status();
    return status.isClean();
  }

  /**
   * 获取 git 状态
   */
  async getStatus(): Promise<StatusResult> {
    return await this.git.status();
  }

  /**
   * 获取状态摘要
   */
  async getStatusSummary(): Promise<{
    isClean: boolean;
    staged: number;
    modified: number;
    deleted: number;
    untracked: number;
    totalChanges: number;
  }> {
    const status = await this.git.status();
    const staged = status.staged.length;
    const modified = status.modified.length;
    const deleted = status.deleted.length;
    const untracked = status.not_added.length;
    const totalChanges = staged + modified + deleted + untracked;

    return {
      isClean: status.isClean(),
      staged,
      modified,
      deleted,
      untracked,
      totalChanges
    };
  }

  /**
   * 检查是否有未提交的更改
   */
  async hasUncommittedChanges(): Promise<boolean> {
    const status = await this.git.status();
    return !status.isClean();
  }

  /**
   * 检查是否有暂存的更改
   */
  async hasStagedChanges(): Promise<boolean> {
    const status = await this.git.status();
    return status.staged.length > 0;
  }

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
  async createBranch(
    branchName: string,
    options: { checkout?: boolean } = {}
  ): Promise<void> {
    const exists = await this.branchExists(branchName);
    if (exists) {
      throw new Error(`branch already exists: ${branchName}`);
    }

    if (options.checkout) {
      await this.ensureCleanWorkingTree();
    }

    await this.git.branch([branchName]);

    if (options.checkout) {
      await this.git.checkout(branchName);
    }
  }

  /**
   * 切换分支
   */
  async checkoutBranch(
    branchName: string,
    options: { force?: boolean } = {}
  ): Promise<void> {
    const exists = await this.branchExists(branchName);
    if (!exists) {
      throw new Error(`branch does not exist: ${branchName}`);
    }

    if (!options.force) {
      await this.ensureCleanWorkingTree();
    }

    const checkoutOptions = options.force ? ['-f', branchName] : [branchName];
    await this.git.checkout(checkoutOptions);
  }

  /**
   * 创建并切换到新分支
   */
  async createAndCheckoutBranch(branchName: string): Promise<void> {
    await this.ensureCleanWorkingTree();

    const exists = await this.branchExists(branchName);
    if (exists) {
      throw new Error(`branch already exists: ${branchName}`);
    }

    await this.git.checkoutLocalBranch(branchName);
  }

  /**
   * 删除分支
   */
  async deleteBranch(
    branchName: string,
    options: { force?: boolean } = {}
  ): Promise<void> {
    const exists = await this.branchExists(branchName);
    if (!exists) {
      throw new Error(`branch does not exist: ${branchName}`);
    }

    const current = await this.getCurrentBranch();
    if (current === branchName) {
      throw new Error(`cannot delete current branch: ${branchName}`);
    }

    const deleteOptions = options.force
      ? ['-D', branchName]
      : ['-d', branchName];
    await this.git.branch(deleteOptions);
  }

  /**
   * 确保工作树干净
   */
  async ensureCleanWorkingTree(): Promise<void> {
    const status = await this.git.status();
    if (!status.isClean()) {
      const summary = await this.getStatusSummary();
      throw new Error(
        `working tree is not clean: ${this.projectPath}\n` +
          `Staged: ${summary.staged}, Modified: ${summary.modified}, ` +
          `Deleted: ${summary.deleted}, Untracked: ${summary.untracked}\n` +
          `Please commit or stash your changes before proceeding.`
      );
    }
  }

  /**
   * 暂存文件
   */
  async stageFiles(files: string[]): Promise<void> {
    await this.git.add(files);
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
  async createCommit(
    message: string,
    options: {
      metadata?: Record<string, string>;
      allowEmpty?: boolean;
      enforceNonDefaultBranch?: boolean;
      force?: boolean;
    } = {}
  ): Promise<void> {
    if (options.enforceNonDefaultBranch && !options.force) {
      const currentBranch = await this.getCurrentBranch();
      const defaultBranches = ['main', 'master', 'develop'];
      if (defaultBranches.includes(currentBranch)) {
        throw new Error(
          `cannot commit to default branch: ${currentBranch}\n` +
            `Please create a feature branch or use force option.`
        );
      }
    }

    if (!options.allowEmpty) {
      const hasStaged = await this.hasStagedChanges();
      if (!hasStaged) {
        throw new Error('no staged changes to commit');
      }
    }

    const commitArgs: string[] = ['commit'];
    commitArgs.push('-m', message);

    if (options.metadata) {
      commitArgs.push('-m', '');
      for (const [key, value] of Object.entries(options.metadata)) {
        commitArgs.push('-m', `[${key}:${value}]`);
      }
    }

    commitArgs.push('--no-gpg-sign');
    if (options.allowEmpty) {
      commitArgs.push('--allow-empty');
    }

    await this.git.raw(commitArgs);
  }

  /**
   * 获取提交日志
   */
  async getCommitLog(options: { maxCount?: number } = {}): Promise<unknown[]> {
    const logOptions: {
      format: Record<string, string>;
      maxCount?: number;
    } = {
      format: {
        hash: '%H',
        date: '%ai',
        message: '%B',
        author_name: '%an',
        author_email: '%ae'
      }
    };
    if (options.maxCount) {
      logOptions.maxCount = options.maxCount;
    }

    const log = await this.git.log(logOptions);
    return [...log.all];
  }

  /**
   * 获取最后一次提交
   */
  async getLastCommit(): Promise<unknown> {
    const log = await this.git.log({
      maxCount: 1,
      format: {
        hash: '%H',
        date: '%ai',
        message: '%B',
        author_name: '%an',
        author_email: '%ae'
      }
    });
    return log.latest;
  }

  /**
   * 获取默认分支
   */
  async getDefaultBranch(): Promise<string> {
    const currentBranch = await this.getCurrentBranch();
    const defaultBranches = ['main', 'master', 'develop'];

    if (defaultBranches.includes(currentBranch)) {
      return currentBranch;
    }

    const branches = await this.listBranches();
    for (const defaultBranch of defaultBranches) {
      if (branches.includes(defaultBranch)) {
        return defaultBranch;
      }
    }

    return 'main';
  }

  /**
   * 检查是否在默认分支上
   */
  async isOnDefaultBranch(): Promise<boolean> {
    const currentBranch = await this.getCurrentBranch();
    const defaultBranches = ['main', 'master', 'develop'];
    return defaultBranches.includes(currentBranch);
  }

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
  async getRemotes(): Promise<unknown[]> {
    return await this.git.getRemotes(true);
  }
}
