/**
 * Git 冲突检测器
 * @module parallel/git/ConflictDetector
 *
 * 检测 Git merge/rebase 冲突，分析冲突级别
 */

import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { ConflictLevel, ConflictInfo } from '../types';

/**
 * ConflictDetector 检测和分析 Git 冲突
 */
export class ConflictDetector {
  /**
   * 检测 Worktree 中的冲突
   * @param worktreePath Worktree 路径
   * @returns 冲突信息数组
   */
  async detectConflicts(worktreePath: string): Promise<ConflictInfo[]> {
    const conflicts: ConflictInfo[] = [];

    try {
      // 获取 git status
      const status = execSync('git status --porcelain', {
        cwd: worktreePath,
        encoding: 'utf-8'
      });

      // 解析冲突文件 (UU = both modified)
      const lines = status.split('\n').filter(l => l.trim());

      for (const line of lines) {
        // UU = unmerged, both modified
        // AA = unmerged, both added
        // DD = unmerged, both deleted
        if (
          line.startsWith('UU ') ||
          line.startsWith('AA ') ||
          line.startsWith('DD ')
        ) {
          const file = line.substring(3).trim();
          const level = this.getConflictLevel(file);
          const markers = await this.getConflictMarkers(worktreePath, file);

          conflicts.push({
            file,
            level,
            conflictMarkers: markers
          });
        }
      }
    } catch (error) {
      // 如果不是 git 仓库或其他错误，返回空数组
    }

    return conflicts;
  }

  /**
   * 检查是否有冲突
   * @param worktreePath Worktree 路径
   * @returns 是否有冲突
   */
  async hasConflicts(worktreePath: string): Promise<boolean> {
    const conflicts = await this.detectConflicts(worktreePath);
    return conflicts.length > 0;
  }

  /**
   * 获取冲突级别
   * @param file 文件路径
   * @returns 冲突级别
   */
  getConflictLevel(file: string): ConflictLevel {
    const basename = path.basename(file);
    const ext = path.extname(file);

    // Level 1: 自动解决 - lockfiles 和配置文件
    const level1Files = [
      'package-lock.json',
      'yarn.lock',
      'pnpm-lock.yaml',
      '.prettierrc',
      '.prettierrc.json',
      '.eslintrc',
      '.eslintrc.json',
      '.editorconfig'
    ];

    if (level1Files.includes(basename)) {
      return 1;
    }

    // Level 1: 自动解决 - 特定扩展名
    const level1Extensions = ['.lock', '.generated'];
    if (level1Extensions.some(e => file.endsWith(e))) {
      return 1;
    }

    // Level 2: AI 辅助解决 - 代码和配置文件
    const level2Extensions = [
      '.ts',
      '.tsx',
      '.js',
      '.jsx',
      '.json',
      '.md',
      '.yaml',
      '.yml',
      '.css',
      '.scss',
      '.html'
    ];

    if (level2Extensions.includes(ext)) {
      return 2;
    }

    // Level 3: 需要人工介入 - 其他文件
    return 3;
  }

  /**
   * 获取冲突标记内容
   * @param worktreePath Worktree 路径
   * @param file 冲突文件路径
   * @returns 冲突标记数组
   */
  private async getConflictMarkers(
    worktreePath: string,
    file: string
  ): Promise<string[]> {
    const markers: string[] = [];
    const filePath = path.join(worktreePath, file);

    if (!fs.existsSync(filePath)) {
      return markers;
    }

    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      const lines = content.split('\n');

      let inConflict = false;
      let currentMarker: string[] = [];

      for (const line of lines) {
        if (line.startsWith('<<<<<<<')) {
          inConflict = true;
          currentMarker = [line];
        } else if (line.startsWith('>>>>>>>')) {
          currentMarker.push(line);
          markers.push(currentMarker.join('\n'));
          currentMarker = [];
          inConflict = false;
        } else if (inConflict) {
          currentMarker.push(line);
        }
      }
    } catch {
      // 忽略读取错误
    }

    return markers;
  }

  /**
   * 获取冲突文件数量
   * @param worktreePath Worktree 路径
   * @returns 各级别冲突数量
   */
  async getConflictStats(worktreePath: string): Promise<{
    total: number;
    level1: number;
    level2: number;
    level3: number;
  }> {
    const conflicts = await this.detectConflicts(worktreePath);

    return {
      total: conflicts.length,
      level1: conflicts.filter(c => c.level === 1).length,
      level2: conflicts.filter(c => c.level === 2).length,
      level3: conflicts.filter(c => c.level === 3).length
    };
  }

  /**
   * 检查是否所有冲突都可自动解决
   * @param worktreePath Worktree 路径
   * @returns 是否可自动解决
   */
  async canAutoResolve(worktreePath: string): Promise<boolean> {
    const stats = await this.getConflictStats(worktreePath);
    return stats.total > 0 && stats.level2 === 0 && stats.level3 === 0;
  }

  /**
   * 检查是否需要人工介入
   * @param worktreePath Worktree 路径
   * @returns 是否需要人工介入
   */
  async needsHumanIntervention(worktreePath: string): Promise<boolean> {
    const stats = await this.getConflictStats(worktreePath);
    return stats.level3 > 0;
  }
}
