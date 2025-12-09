/**
 * Git 检查器 - 检查 Git 仓库状态
 */

import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';
import { Checker, CheckResult } from '../types';

export class GitChecker implements Checker {
  category = 'Git';
  icon = '🔧';

  constructor(private projectRoot: string) {}

  async check(): Promise<CheckResult[]> {
    const results: CheckResult[] = [];

    // 1. 检查是否是 Git 仓库
    results.push(this.checkIsRepo());

    // 2. 检查主分支
    results.push(this.checkMainBranch());

    return results;
  }

  private checkIsRepo(): CheckResult {
    const gitPath = path.join(this.projectRoot, '.git');
    if (fs.existsSync(gitPath)) {
      return {
        name: 'Git 仓库',
        status: 'pass',
        message: '是 Git 仓库'
      };
    }
    return {
      name: 'Git 仓库',
      status: 'warn',
      message: '不是 Git 仓库',
      detail: '运行 git init 初始化'
    };
  }

  private checkMainBranch(): CheckResult {
    try {
      const branch = execSync('git rev-parse --abbrev-ref HEAD', {
        cwd: this.projectRoot,
        encoding: 'utf-8'
      }).trim();

      return {
        name: '当前分支',
        status: 'pass',
        message: branch
      };
    } catch {
      return {
        name: '当前分支',
        status: 'warn',
        message: '无法获取分支信息'
      };
    }
  }
}
