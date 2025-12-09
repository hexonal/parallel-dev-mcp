/**
 * Claude 检查器 - 检查 .claude 目录配置
 */

import * as fs from 'fs';
import * as path from 'path';
import { Checker, CheckResult } from '../types';
import { CLAUDE_PATHS } from '../../config';

export class ClaudeChecker implements Checker {
  category = 'Claude (.claude)';
  icon = '📦';

  constructor(private projectRoot: string) {}

  async check(): Promise<CheckResult[]> {
    const results: CheckResult[] = [];

    // 1. 检查 .claude 目录
    results.push(this.checkDirectory());

    // 2. 检查 settings.json
    results.push(this.checkSettingsJson());

    // 3. 检查 commands 目录
    results.push(this.checkCommandsDir());

    // 4. 检查命令文件格式
    results.push(await this.checkCommandsFormat());

    // 5. 检查 agents 目录
    results.push(this.checkAgentsDir());

    // 6. 检查 skills 目录
    results.push(this.checkSkillsDir());

    return results;
  }

  private checkDirectory(): CheckResult {
    const claudePath = path.join(this.projectRoot, CLAUDE_PATHS.root);
    if (fs.existsSync(claudePath)) {
      return {
        name: '.claude 目录',
        status: 'pass',
        message: '目录存在'
      };
    }
    return {
      name: '.claude 目录',
      status: 'fail',
      message: '目录不存在',
      detail: '运行 pdev init 初始化项目'
    };
  }

  private checkSettingsJson(): CheckResult {
    const settingsPath = path.join(this.projectRoot, CLAUDE_PATHS.settings);
    if (!fs.existsSync(settingsPath)) {
      return {
        name: 'settings.json',
        status: 'fail',
        message: '文件不存在'
      };
    }

    try {
      const content = fs.readFileSync(settingsPath, 'utf-8');
      JSON.parse(content);
      return {
        name: 'settings.json',
        status: 'pass',
        message: 'JSON 有效'
      };
    } catch {
      return {
        name: 'settings.json',
        status: 'fail',
        message: 'JSON 格式无效'
      };
    }
  }

  private checkCommandsDir(): CheckResult {
    const commandsPath = path.join(this.projectRoot, CLAUDE_PATHS.root, 'commands');
    if (!fs.existsSync(commandsPath)) {
      return {
        name: 'commands 目录',
        status: 'fail',
        message: '目录不存在'
      };
    }

    const files = fs.readdirSync(commandsPath).filter(f => f.endsWith('.md') && f !== 'README.md');
    if (files.length === 0) {
      return {
        name: 'commands 目录',
        status: 'warn',
        message: '目录为空'
      };
    }

    return {
      name: 'commands 目录',
      status: 'pass',
      message: `${files.length} 个命令`
    };
  }

  private async checkCommandsFormat(): Promise<CheckResult> {
    const commandsPath = path.join(this.projectRoot, CLAUDE_PATHS.root, 'commands');
    if (!fs.existsSync(commandsPath)) {
      return {
        name: '命令格式',
        status: 'fail',
        message: 'commands 目录不存在'
      };
    }

    const files = fs.readdirSync(commandsPath).filter(f => f.endsWith('.md') && f !== 'README.md');
    const errors: string[] = [];

    for (const file of files) {
      const filePath = path.join(commandsPath, file);
      const content = fs.readFileSync(filePath, 'utf-8');

      // 检查祈使句
      const hasImperative = /^请执行|^运行|^读取|^执行/m.test(content);
      // 检查 bash 代码块
      const hasBashBlock = content.includes('```bash');

      if (!hasImperative || !hasBashBlock) {
        errors.push(file);
      }
    }

    if (errors.length > 0) {
      return {
        name: '命令格式',
        status: 'warn',
        message: `${errors.length} 个命令格式不规范`,
        detail: errors.join(', ')
      };
    }

    return {
      name: '命令格式',
      status: 'pass',
      message: '所有命令格式正确'
    };
  }

  private checkAgentsDir(): CheckResult {
    const agentsPath = path.join(this.projectRoot, CLAUDE_PATHS.root, 'agents');
    if (!fs.existsSync(agentsPath)) {
      return {
        name: 'agents 目录',
        status: 'warn',
        message: '目录不存在'
      };
    }

    const files = fs.readdirSync(agentsPath).filter(f => f.endsWith('.md'));
    if (files.length === 0) {
      return {
        name: 'agents 目录',
        status: 'warn',
        message: '目录为空'
      };
    }

    return {
      name: 'agents 目录',
      status: 'pass',
      message: `${files.length} 个 agent`
    };
  }

  private checkSkillsDir(): CheckResult {
    const skillsPath = path.join(this.projectRoot, CLAUDE_PATHS.root, 'skills');
    if (!fs.existsSync(skillsPath)) {
      return {
        name: 'skills 目录',
        status: 'warn',
        message: '目录不存在'
      };
    }

    const dirs = fs.readdirSync(skillsPath, { withFileTypes: true })
      .filter(d => d.isDirectory());

    if (dirs.length === 0) {
      return {
        name: 'skills 目录',
        status: 'warn',
        message: '目录为空'
      };
    }

    return {
      name: 'skills 目录',
      status: 'pass',
      message: `${dirs.length} 个技能`
    };
  }
}
