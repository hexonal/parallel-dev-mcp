/**
 * 健康检查主类 - 协调所有检查器
 */

import chalk from 'chalk';
import { Checker, CheckResult, CategoryResult, DiagnosticResult } from './types';
import { ConfigChecker } from './checks/ConfigChecker';
import { ClaudeChecker } from './checks/ClaudeChecker';
import { McpChecker } from './checks/McpChecker';
import { GitChecker } from './checks/GitChecker';
import { RootClaudeChecker } from './checks/RootClaudeChecker';
import { initProject } from '../init';

export class HealthChecker {
  private checkers: Checker[];

  constructor(private projectRoot: string) {
    this.checkers = [
      new ConfigChecker(projectRoot),
      new ClaudeChecker(projectRoot),
      new McpChecker(projectRoot),
      new RootClaudeChecker(projectRoot),
      new GitChecker(projectRoot),
    ];
  }

  /**
   * 运行所有检查
   */
  async runAllChecks(): Promise<DiagnosticResult> {
    const categories: CategoryResult[] = [];
    let totalPassed = 0;
    let totalWarnings = 0;
    let totalFailed = 0;

    for (const checker of this.checkers) {
      const checks = await checker.check();

      let passed = 0;
      let warnings = 0;
      let failed = 0;

      for (const check of checks) {
        if (check.status === 'pass') passed++;
        else if (check.status === 'warn') warnings++;
        else failed++;
      }

      categories.push({
        category: checker.category,
        icon: checker.icon,
        checks,
        passed,
        warnings,
        failed
      });

      totalPassed += passed;
      totalWarnings += warnings;
      totalFailed += failed;
    }

    return {
      categories,
      totalPassed,
      totalWarnings,
      totalFailed,
      healthy: totalFailed === 0
    };
  }

  /**
   * 运行指定类别的检查
   */
  async runCategory(categoryName: string): Promise<CategoryResult | null> {
    const checker = this.checkers.find(c =>
      c.category.toLowerCase().includes(categoryName.toLowerCase())
    );

    if (!checker) {
      return null;
    }

    const checks = await checker.check();
    let passed = 0;
    let warnings = 0;
    let failed = 0;

    for (const check of checks) {
      if (check.status === 'pass') passed++;
      else if (check.status === 'warn') warnings++;
      else failed++;
    }

    return {
      category: checker.category,
      icon: checker.icon,
      checks,
      passed,
      warnings,
      failed
    };
  }

  /**
   * 自动修复 - 重新运行 init
   */
  async fix(): Promise<boolean> {
    try {
      const result = await initProject(this.projectRoot, { force: true, silent: true });
      return result.success;
    } catch {
      return false;
    }
  }

  /**
   * 打印诊断结果
   */
  printResult(result: DiagnosticResult): void {
    console.log();
    console.log(chalk.bold('🏥 ParallelDev 环境诊断'));
    console.log();

    for (const category of result.categories) {
      console.log(chalk.bold(`${category.icon} ${category.category}`));

      for (const check of category.checks) {
        const icon = this.getStatusIcon(check.status);
        const message = this.getStatusColor(check.status, check.message);
        console.log(`  ${icon} ${check.name}: ${message}`);

        if (check.detail && check.status !== 'pass') {
          console.log(chalk.gray(`     ${check.detail}`));
        }
      }
      console.log();
    }

    // 汇总
    console.log('━'.repeat(40));
    console.log(
      `${chalk.green(`✅ 通过: ${result.totalPassed}`)}  ` +
      `${chalk.yellow(`⚠️ 警告: ${result.totalWarnings}`)}  ` +
      `${chalk.red(`❌ 失败: ${result.totalFailed}`)}`
    );
    console.log();

    if (result.healthy) {
      console.log(chalk.green.bold('🎉 ParallelDev 环境配置正常！'));
    } else {
      console.log(chalk.red.bold('❌ 环境配置存在问题，请运行 pdev doctor --fix 修复'));
    }
    console.log();
  }

  /**
   * 输出 JSON 格式
   */
  printJson(result: DiagnosticResult): void {
    console.log(JSON.stringify(result, null, 2));
  }

  private getStatusIcon(status: string): string {
    switch (status) {
      case 'pass': return chalk.green('✅');
      case 'warn': return chalk.yellow('⚠️');
      case 'fail': return chalk.red('❌');
      default: return '  ';
    }
  }

  private getStatusColor(status: string, message: string): string {
    switch (status) {
      case 'pass': return chalk.green(message);
      case 'warn': return chalk.yellow(message);
      case 'fail': return chalk.red(message);
      default: return message;
    }
  }
}
