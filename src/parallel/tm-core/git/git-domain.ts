/**
 * Git Domain Facade
 * 爆改自 claude-task-master/packages/tm-core/src/modules/git/git-domain.ts
 * Git 操作的统一 API
 */

import type { StatusResult } from 'simple-git';
import { GitAdapter } from './git-adapter';

/**
 * Git Domain - Git 操作的统一 API
 */
export class GitDomain {
  private gitAdapter: GitAdapter;

  constructor(projectPath: string) {
    this.gitAdapter = new GitAdapter(projectPath);
  }

  // ========== 仓库验证 ==========

  /**
   * 检查目录是否为 git 仓库
   */
  async isGitRepository(): Promise<boolean> {
    return this.gitAdapter.isGitRepository();
  }

  /**
   * 确保在有效的 git 仓库中
   */
  async ensureGitRepository(): Promise<void> {
    return this.gitAdapter.ensureGitRepository();
  }

  /**
   * 获取仓库根路径
   */
  async getRepositoryRoot(): Promise<string> {
    return this.gitAdapter.getRepositoryRoot();
  }

  // ========== 工作树状态 ==========

  /**
   * 检查工作树是否干净
   */
  async isWorkingTreeClean(): Promise<boolean> {
    return this.gitAdapter.isWorkingTreeClean();
  }

  /**
   * 获取 git 状态
   */
  async getStatus(): Promise<StatusResult> {
    return this.gitAdapter.getStatus();
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
    return this.gitAdapter.getStatusSummary();
  }

  /**
   * 检查是否有未提交的更改
   */
  async hasUncommittedChanges(): Promise<boolean> {
    return this.gitAdapter.hasUncommittedChanges();
  }

  /**
   * 检查是否有暂存的更改
   */
  async hasStagedChanges(): Promise<boolean> {
    return this.gitAdapter.hasStagedChanges();
  }

  // ========== 分支操作 ==========

  /**
   * 获取当前分支名
   */
  async getCurrentBranch(): Promise<string> {
    return this.gitAdapter.getCurrentBranch();
  }

  /**
   * 列出所有本地分支
   */
  async listBranches(): Promise<string[]> {
    return this.gitAdapter.listBranches();
  }

  /**
   * 检查分支是否存在
   */
  async branchExists(branchName: string): Promise<boolean> {
    return this.gitAdapter.branchExists(branchName);
  }

  /**
   * 创建新分支
   */
  async createBranch(
    branchName: string,
    options?: { checkout?: boolean }
  ): Promise<void> {
    return this.gitAdapter.createBranch(branchName, options);
  }

  /**
   * 切换分支
   */
  async checkoutBranch(
    branchName: string,
    options?: { force?: boolean }
  ): Promise<void> {
    return this.gitAdapter.checkoutBranch(branchName, options);
  }

  /**
   * 创建并切换到新分支
   */
  async createAndCheckoutBranch(branchName: string): Promise<void> {
    return this.gitAdapter.createAndCheckoutBranch(branchName);
  }

  /**
   * 删除分支
   */
  async deleteBranch(
    branchName: string,
    options?: { force?: boolean }
  ): Promise<void> {
    return this.gitAdapter.deleteBranch(branchName, options);
  }

  /**
   * 获取默认分支名
   */
  async getDefaultBranch(): Promise<string> {
    return this.gitAdapter.getDefaultBranch();
  }

  /**
   * 检查是否在默认分支上
   */
  async isOnDefaultBranch(): Promise<boolean> {
    return this.gitAdapter.isOnDefaultBranch();
  }

  // ========== 提交操作 ==========

  /**
   * 暂存文件
   */
  async stageFiles(files: string[]): Promise<void> {
    return this.gitAdapter.stageFiles(files);
  }

  /**
   * 取消暂存
   */
  async unstageFiles(files: string[]): Promise<void> {
    return this.gitAdapter.unstageFiles(files);
  }

  /**
   * 创建提交
   */
  async createCommit(
    message: string,
    options?: {
      metadata?: Record<string, string>;
      allowEmpty?: boolean;
      enforceNonDefaultBranch?: boolean;
      force?: boolean;
    }
  ): Promise<void> {
    return this.gitAdapter.createCommit(message, options);
  }

  /**
   * 获取提交日志
   */
  async getCommitLog(options?: { maxCount?: number }): Promise<unknown[]> {
    return this.gitAdapter.getCommitLog(options);
  }

  /**
   * 获取最后一次提交
   */
  async getLastCommit(): Promise<unknown> {
    return this.gitAdapter.getLastCommit();
  }

  // ========== 远程操作 ==========

  /**
   * 检查是否有远程仓库
   */
  async hasRemote(): Promise<boolean> {
    return this.gitAdapter.hasRemote();
  }

  /**
   * 获取所有远程仓库
   */
  async getRemotes(): Promise<unknown[]> {
    return this.gitAdapter.getRemotes();
  }
}
