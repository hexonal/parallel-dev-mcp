/**
 * Config 检查器 - 检查 .pdev 目录配置
 */

import * as fs from 'fs';
import * as path from 'path';
import { Checker, CheckResult } from '../types';
import { PDEV_PATHS } from '../../config';

export class ConfigChecker implements Checker {
  category = 'Config (.pdev)';
  icon = '📁';

  constructor(private projectRoot: string) {}

  async check(): Promise<CheckResult[]> {
    const results: CheckResult[] = [];

    // 1. 检查 .pdev 目录
    results.push(this.checkDirectory());

    // 2. 检查 config.json
    results.push(this.checkConfigJson());

    // 3. 检查 state.json
    results.push(this.checkStateJson());

    // 4. 检查 tasks/tasks.json
    results.push(this.checkTasksJson());

    // 5. 检查 CLAUDE.md
    results.push(this.checkClaudeMd());

    return results;
  }

  private checkDirectory(): CheckResult {
    const pdevPath = path.join(this.projectRoot, PDEV_PATHS.root);
    if (fs.existsSync(pdevPath)) {
      return {
        name: '.pdev 目录',
        status: 'pass',
        message: '目录存在'
      };
    }
    return {
      name: '.pdev 目录',
      status: 'fail',
      message: '目录不存在',
      detail: '运行 pdev init 初始化项目'
    };
  }

  private checkConfigJson(): CheckResult {
    const configPath = path.join(this.projectRoot, PDEV_PATHS.config);
    if (!fs.existsSync(configPath)) {
      return {
        name: 'config.json',
        status: 'fail',
        message: '文件不存在'
      };
    }

    try {
      const content = fs.readFileSync(configPath, 'utf-8');
      JSON.parse(content);
      return {
        name: 'config.json',
        status: 'pass',
        message: 'JSON 有效'
      };
    } catch {
      return {
        name: 'config.json',
        status: 'fail',
        message: 'JSON 格式无效'
      };
    }
  }

  private checkStateJson(): CheckResult {
    const statePath = path.join(this.projectRoot, PDEV_PATHS.state);
    if (!fs.existsSync(statePath)) {
      return {
        name: 'state.json',
        status: 'fail',
        message: '文件不存在'
      };
    }

    try {
      const content = fs.readFileSync(statePath, 'utf-8');
      JSON.parse(content);
      return {
        name: 'state.json',
        status: 'pass',
        message: 'JSON 有效'
      };
    } catch {
      return {
        name: 'state.json',
        status: 'fail',
        message: 'JSON 格式无效'
      };
    }
  }

  private checkTasksJson(): CheckResult {
    const tasksPath = path.join(this.projectRoot, PDEV_PATHS.tasksJson);
    if (!fs.existsSync(tasksPath)) {
      return {
        name: 'tasks/tasks.json',
        status: 'warn',
        message: '文件不存在',
        detail: '运行 pdev generate 生成任务'
      };
    }

    try {
      const content = fs.readFileSync(tasksPath, 'utf-8');
      JSON.parse(content);
      return {
        name: 'tasks/tasks.json',
        status: 'pass',
        message: 'JSON 有效'
      };
    } catch {
      return {
        name: 'tasks/tasks.json',
        status: 'fail',
        message: 'JSON 格式无效'
      };
    }
  }

  private checkClaudeMd(): CheckResult {
    const claudeMdPath = path.join(this.projectRoot, PDEV_PATHS.claudeMd);
    if (fs.existsSync(claudeMdPath)) {
      return {
        name: 'CLAUDE.md (Worker)',
        status: 'pass',
        message: '文件存在'
      };
    }
    return {
      name: 'CLAUDE.md (Worker)',
      status: 'fail',
      message: '文件不存在'
    };
  }
}
