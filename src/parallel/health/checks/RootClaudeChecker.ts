/**
 * 根目录 CLAUDE.md 检查器
 */

import * as fs from 'fs';
import * as path from 'path';
import { Checker, CheckResult } from '../types';

/** ParallelDev 集成标记 */
const INTEGRATION_MARKER = '# ParallelDev 集成';

export class RootClaudeChecker implements Checker {
  category = '项目指令';
  icon = '📄';

  constructor(private projectRoot: string) {}

  async check(): Promise<CheckResult[]> {
    const results: CheckResult[] = [];

    // 1. 检查 CLAUDE.md 文件
    results.push(this.checkFile());

    // 2. 检查 ParallelDev 集成标记
    results.push(this.checkIntegrationMarker());

    return results;
  }

  private checkFile(): CheckResult {
    const claudeMdPath = path.join(this.projectRoot, 'CLAUDE.md');
    if (fs.existsSync(claudeMdPath)) {
      return {
        name: 'CLAUDE.md',
        status: 'pass',
        message: '文件存在'
      };
    }
    return {
      name: 'CLAUDE.md',
      status: 'warn',
      message: '文件不存在',
      detail: '运行 pdev init 创建'
    };
  }

  private checkIntegrationMarker(): CheckResult {
    const claudeMdPath = path.join(this.projectRoot, 'CLAUDE.md');

    if (!fs.existsSync(claudeMdPath)) {
      return {
        name: 'ParallelDev 集成',
        status: 'fail',
        message: 'CLAUDE.md 不存在'
      };
    }

    const content = fs.readFileSync(claudeMdPath, 'utf-8');
    if (content.includes(INTEGRATION_MARKER)) {
      return {
        name: 'ParallelDev 集成',
        status: 'pass',
        message: '已集成'
      };
    }

    return {
      name: 'ParallelDev 集成',
      status: 'warn',
      message: '未包含集成标记',
      detail: '运行 pdev init 追加集成说明'
    };
  }
}
