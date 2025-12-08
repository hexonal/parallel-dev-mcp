/**
 * ConflictResolver - 冲突解决器
 *
 * 实现分层冲突解决策略：
 * - Level 1: 自动解决（lockfiles, 格式化）
 * - Level 2: AI 辅助解决
 * - Level 3: 标记需要人工介入
 */

import { spawn } from 'child_process';
import * as fs from 'fs/promises';
import * as path from 'path';
import { EventEmitter } from 'events';
import {
  SubagentRunner,
  ConflictInfo,
  ResolveResult,
} from './SubagentRunner';

/**
 * 冲突检测结果
 */
export interface ConflictDetectionResult {
  hasConflicts: boolean;
  conflicts: ConflictInfo[];
}

/**
 * 冲突解决器配置
 */
export interface ConflictResolverConfig {
  projectRoot: string;
  subagentRunner: SubagentRunner;
  autoResolvePatterns?: string[];
}

/**
 * ConflictResolver 类
 *
 * 分层冲突解决策略实现
 */
export class ConflictResolver extends EventEmitter {
  private projectRoot: string;
  private subagent: SubagentRunner;
  private autoResolvePatterns: string[];

  // 默认自动解决的文件模式
  private static DEFAULT_AUTO_RESOLVE_PATTERNS = [
    'package-lock.json',
    'yarn.lock',
    'pnpm-lock.yaml',
    'bun.lockb',
    '.prettierrc',
    '.eslintrc',
    'tsconfig.json',
  ];

  constructor(config: ConflictResolverConfig) {
    super();
    this.projectRoot = config.projectRoot;
    this.subagent = config.subagentRunner;
    this.autoResolvePatterns = config.autoResolvePatterns ||
      ConflictResolver.DEFAULT_AUTO_RESOLVE_PATTERNS;
  }

  /**
   * 检测冲突
   *
   * @param worktreePath Worktree 路径
   */
  async detectConflicts(worktreePath: string): Promise<ConflictDetectionResult> {
    try {
      // 运行 git status 检测冲突
      const output = await this.runGitCommand(worktreePath, ['status', '--porcelain']);

      const conflicts: ConflictInfo[] = [];

      // 解析 git status 输出
      const lines = output.split('\n').filter(Boolean);

      for (const line of lines) {
        const status = line.substring(0, 2);
        const file = line.substring(3);

        // UU = 双方修改，AA = 双方新增，DD = 双方删除
        if (status === 'UU' || status === 'AA' || status === 'DD') {
          conflicts.push(this.createConflictInfo(file, status));
        }
      }

      return {
        hasConflicts: conflicts.length > 0,
        conflicts,
      };
    } catch (error) {
      this.emit('error', `Failed to detect conflicts: ${error}`);
      return { hasConflicts: false, conflicts: [] };
    }
  }

  /**
   * 分层解决冲突
   *
   * @param worktreePath Worktree 路径
   */
  async resolve(worktreePath: string): Promise<ResolveResult> {
    this.emit('start', { worktreePath });

    // 1. 检测冲突
    const detection = await this.detectConflicts(worktreePath);

    if (!detection.hasConflicts) {
      return {
        success: true,
        resolved: [],
        unresolved: [],
        needsHumanReview: [],
        summary: 'No conflicts detected',
      };
    }

    const resolved: ConflictInfo[] = [];
    const unresolved: ConflictInfo[] = [];
    const needsHumanReview: ConflictInfo[] = [];

    // 分类冲突
    const level1Conflicts: ConflictInfo[] = [];
    const level2Conflicts: ConflictInfo[] = [];
    const level3Conflicts: ConflictInfo[] = [];

    for (const conflict of detection.conflicts) {
      if (this.isAutoResolvable(conflict)) {
        level1Conflicts.push(conflict);
      } else if (conflict.severity === 'high') {
        level3Conflicts.push(conflict);
      } else {
        level2Conflicts.push(conflict);
      }
    }

    // 2. Level 1: 自动解决
    if (level1Conflicts.length > 0) {
      this.emit('level1', { count: level1Conflicts.length });

      const level1Results = await this.resolveLevel1(worktreePath, level1Conflicts);
      resolved.push(...level1Results.resolved);
      unresolved.push(...level1Results.unresolved);
    }

    // 3. Level 2: AI 辅助解决
    if (level2Conflicts.length > 0) {
      this.emit('level2', { count: level2Conflicts.length });

      const level2Results = await this.resolveLevel2(worktreePath, level2Conflicts);
      resolved.push(...level2Results.resolved);
      unresolved.push(...level2Results.unresolved);
      needsHumanReview.push(...level2Results.needsHumanReview);
    }

    // 4. Level 3: 标记需要人工介入
    if (level3Conflicts.length > 0) {
      this.emit('level3', { count: level3Conflicts.length });

      this.markForHumanReview(level3Conflicts);
      needsHumanReview.push(...level3Conflicts);
    }

    const success = unresolved.length === 0 && needsHumanReview.length === 0;

    const result: ResolveResult = {
      success,
      resolved,
      unresolved,
      needsHumanReview,
      summary: this.generateSummary(resolved, unresolved, needsHumanReview),
    };

    this.emit('complete', result);

    return result;
  }

  /**
   * Level 1: 自动解决
   *
   * 处理 lockfiles、格式化文件等
   */
  private async resolveLevel1(
    worktreePath: string,
    conflicts: ConflictInfo[]
  ): Promise<{ resolved: ConflictInfo[]; unresolved: ConflictInfo[] }> {
    const resolved: ConflictInfo[] = [];
    const unresolved: ConflictInfo[] = [];

    for (const conflict of conflicts) {
      try {
        const filePath = path.join(worktreePath, conflict.file);

        // 对于 lockfiles，使用 theirs 版本（主分支）
        if (this.isLockfile(conflict.file)) {
          await this.runGitCommand(worktreePath, ['checkout', '--theirs', conflict.file]);
          await this.runGitCommand(worktreePath, ['add', conflict.file]);
          resolved.push(conflict);
          this.emit('resolved', { conflict, level: 1 });
        }
        // 对于配置文件，尝试合并
        else if (this.isConfigFile(conflict.file)) {
          await this.runGitCommand(worktreePath, ['checkout', '--theirs', conflict.file]);
          await this.runGitCommand(worktreePath, ['add', conflict.file]);
          resolved.push(conflict);
          this.emit('resolved', { conflict, level: 1 });
        }
        else {
          unresolved.push(conflict);
        }
      } catch (error) {
        this.emit('error', `Failed to resolve ${conflict.file}: ${error}`);
        unresolved.push(conflict);
      }
    }

    return { resolved, unresolved };
  }

  /**
   * Level 2: AI 辅助解决
   *
   * 使用 Subagent 分析和解决冲突
   */
  private async resolveLevel2(
    worktreePath: string,
    conflicts: ConflictInfo[]
  ): Promise<{
    resolved: ConflictInfo[];
    unresolved: ConflictInfo[];
    needsHumanReview: ConflictInfo[];
  }> {
    // 调用 conflict-resolver subagent
    const result = await this.subagent.runConflictResolver(worktreePath, conflicts);

    // 对于成功解决的冲突，执行 git add
    for (const conflict of result.resolved) {
      try {
        await this.runGitCommand(worktreePath, ['add', conflict.file]);
        this.emit('resolved', { conflict, level: 2 });
      } catch (error) {
        this.emit('error', `Failed to stage ${conflict.file}: ${error}`);
      }
    }

    return {
      resolved: result.resolved,
      unresolved: result.unresolved,
      needsHumanReview: result.needsHumanReview,
    };
  }

  /**
   * Level 3: 标记需要人工介入
   */
  private markForHumanReview(conflicts: ConflictInfo[]): void {
    for (const conflict of conflicts) {
      this.emit('humanReview', {
        file: conflict.file,
        reason: `High severity conflict requires human review: ${conflict.description}`,
      });
    }
  }

  /**
   * 判断是否可自动解决
   */
  private isAutoResolvable(conflict: ConflictInfo): boolean {
    return this.autoResolvePatterns.some((pattern) =>
      conflict.file.endsWith(pattern) || conflict.file.includes(pattern)
    );
  }

  /**
   * 判断是否为 lockfile
   */
  private isLockfile(file: string): boolean {
    const lockfiles = ['package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'bun.lockb'];
    return lockfiles.some((lf) => file.endsWith(lf));
  }

  /**
   * 判断是否为配置文件
   */
  private isConfigFile(file: string): boolean {
    const configFiles = ['.prettierrc', '.eslintrc', 'tsconfig.json', '.editorconfig'];
    return configFiles.some((cf) => file.endsWith(cf) || file.includes(cf));
  }

  /**
   * 创建冲突信息
   */
  private createConflictInfo(file: string, status: string): ConflictInfo {
    let type: 'content' | 'rename' | 'delete' = 'content';
    let severity: 'low' | 'medium' | 'high' = 'medium';

    if (status === 'DD') {
      type = 'delete';
      severity = 'low';
    } else if (status === 'AA') {
      type = 'content';
      severity = 'high';
    }

    // 根据文件类型调整严重级别
    if (this.isLockfile(file)) {
      severity = 'low';
    } else if (file.includes('src/') || file.includes('lib/')) {
      severity = 'high';
    }

    return {
      file,
      type,
      severity,
      description: `Git conflict status: ${status}`,
    };
  }

  /**
   * 生成解决报告摘要
   */
  private generateSummary(
    resolved: ConflictInfo[],
    unresolved: ConflictInfo[],
    needsHumanReview: ConflictInfo[]
  ): string {
    const parts: string[] = [];

    if (resolved.length > 0) {
      parts.push(`✅ Resolved: ${resolved.length} conflicts`);
    }

    if (unresolved.length > 0) {
      parts.push(`❌ Unresolved: ${unresolved.length} conflicts`);
    }

    if (needsHumanReview.length > 0) {
      parts.push(`⚠️ Needs human review: ${needsHumanReview.length} conflicts`);
    }

    return parts.join(' | ') || 'No conflicts processed';
  }

  /**
   * 执行 Git 命令
   */
  private runGitCommand(cwd: string, args: string[]): Promise<string> {
    return new Promise((resolve, reject) => {
      const child = spawn('git', args, { cwd });

      let stdout = '';
      let stderr = '';

      child.stdout?.on('data', (data) => {
        stdout += data.toString();
      });

      child.stderr?.on('data', (data) => {
        stderr += data.toString();
      });

      child.on('close', (code) => {
        if (code === 0) {
          resolve(stdout);
        } else {
          reject(new Error(`Git command failed: ${stderr}`));
        }
      });

      child.on('error', reject);
    });
  }
}
