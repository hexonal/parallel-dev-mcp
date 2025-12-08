/**
 * CodeValidator - 代码验证器
 *
 * 负责运行 TypeScript 类型检查、ESLint 和单元测试
 */

import { spawn } from 'child_process';
import * as path from 'path';
import * as fs from 'fs/promises';
import { EventEmitter } from 'events';

/**
 * 检查结果
 */
export interface CheckResult {
  passed: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * 测试结果
 */
export interface TestResult {
  passed: boolean;
  total: number;
  failed: number;
  skipped: number;
  failures: string[];
}

/**
 * 验证结果
 */
export interface ValidationResult {
  passed: boolean;
  typeCheck: CheckResult;
  lint: CheckResult;
  tests: TestResult;
  summary: string;
  duration: number;
}

/**
 * 验证器配置
 */
export interface CodeValidatorConfig {
  projectRoot: string;
  timeout?: number;
  skipTests?: boolean;
  skipLint?: boolean;
  skipTypeCheck?: boolean;
}

/**
 * CodeValidator 类
 *
 * 运行代码质量检查
 */
export class CodeValidator extends EventEmitter {
  private projectRoot: string;
  private timeout: number;
  private skipTests: boolean;
  private skipLint: boolean;
  private skipTypeCheck: boolean;

  constructor(config: CodeValidatorConfig) {
    super();
    this.projectRoot = config.projectRoot;
    this.timeout = config.timeout || 120000;
    this.skipTests = config.skipTests || false;
    this.skipLint = config.skipLint || false;
    this.skipTypeCheck = config.skipTypeCheck || false;
  }

  /**
   * 运行所有验证
   *
   * @param worktreePath Worktree 路径
   */
  async validate(worktreePath: string): Promise<ValidationResult> {
    const startTime = Date.now();

    this.emit('start', { worktreePath });

    // 并行运行检查
    const [typeCheck, lint, tests] = await Promise.all([
      this.skipTypeCheck
        ? this.createSkippedCheckResult()
        : this.runTypeCheck(worktreePath),
      this.skipLint
        ? this.createSkippedCheckResult()
        : this.runLint(worktreePath),
      this.skipTests
        ? this.createSkippedTestResult()
        : this.runTests(worktreePath),
    ]);

    const passed = typeCheck.passed && lint.passed && tests.passed;
    const duration = Date.now() - startTime;

    const result: ValidationResult = {
      passed,
      typeCheck,
      lint,
      tests,
      summary: this.generateSummary(typeCheck, lint, tests),
      duration,
    };

    this.emit('complete', result);

    return result;
  }

  /**
   * TypeScript 类型检查
   *
   * @param worktreePath Worktree 路径
   */
  async runTypeCheck(worktreePath: string): Promise<CheckResult> {
    this.emit('typeCheck:start');

    try {
      // 检查是否存在 tsconfig.json
      const tsconfigPath = path.join(worktreePath, 'tsconfig.json');
      const hasTsconfig = await this.fileExists(tsconfigPath);

      if (!hasTsconfig) {
        return {
          passed: true,
          errors: [],
          warnings: ['tsconfig.json not found, skipping type check'],
        };
      }

      const { stdout, stderr, code } = await this.runCommand(
        'npx',
        ['tsc', '--noEmit', '--pretty', 'false'],
        worktreePath
      );

      const output = stdout + stderr;
      const errors = this.parseTypeScriptErrors(output);

      const result: CheckResult = {
        passed: code === 0,
        errors,
        warnings: [],
      };

      this.emit('typeCheck:complete', result);

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

      return {
        passed: false,
        errors: [`TypeScript check failed: ${errorMessage}`],
        warnings: [],
      };
    }
  }

  /**
   * ESLint 检查
   *
   * @param worktreePath Worktree 路径
   */
  async runLint(worktreePath: string): Promise<CheckResult> {
    this.emit('lint:start');

    try {
      // 检查是否存在 ESLint 配置
      const hasEslint = await this.hasEslintConfig(worktreePath);

      if (!hasEslint) {
        return {
          passed: true,
          errors: [],
          warnings: ['ESLint config not found, skipping lint check'],
        };
      }

      const { stdout, stderr, code } = await this.runCommand(
        'npx',
        ['eslint', '.', '--format', 'compact', '--max-warnings', '0'],
        worktreePath
      );

      const output = stdout + stderr;
      const { errors, warnings } = this.parseEslintOutput(output);

      const result: CheckResult = {
        passed: code === 0,
        errors,
        warnings,
      };

      this.emit('lint:complete', result);

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

      return {
        passed: false,
        errors: [`ESLint check failed: ${errorMessage}`],
        warnings: [],
      };
    }
  }

  /**
   * 运行单元测试
   *
   * @param worktreePath Worktree 路径
   */
  async runTests(worktreePath: string): Promise<TestResult> {
    this.emit('tests:start');

    try {
      // 检查是否存在测试脚本
      const hasTestScript = await this.hasTestScript(worktreePath);

      if (!hasTestScript) {
        return {
          passed: true,
          total: 0,
          failed: 0,
          skipped: 0,
          failures: [],
        };
      }

      const { stdout, stderr, code } = await this.runCommand(
        'npm',
        ['test', '--', '--passWithNoTests'],
        worktreePath
      );

      const output = stdout + stderr;
      const testResult = this.parseTestOutput(output, code);

      this.emit('tests:complete', testResult);

      return testResult;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

      return {
        passed: false,
        total: 0,
        failed: 1,
        skipped: 0,
        failures: [`Test execution failed: ${errorMessage}`],
      };
    }
  }

  /**
   * 执行命令
   */
  private runCommand(
    command: string,
    args: string[],
    cwd: string
  ): Promise<{ stdout: string; stderr: string; code: number }> {
    return new Promise((resolve) => {
      const child = spawn(command, args, {
        cwd,
        timeout: this.timeout,
        shell: true,
      });

      let stdout = '';
      let stderr = '';

      child.stdout?.on('data', (data) => {
        stdout += data.toString();
      });

      child.stderr?.on('data', (data) => {
        stderr += data.toString();
      });

      child.on('close', (code) => {
        resolve({ stdout, stderr, code: code || 0 });
      });

      child.on('error', (err) => {
        resolve({ stdout, stderr, code: 1 });
      });
    });
  }

  /**
   * 解析 TypeScript 错误
   */
  private parseTypeScriptErrors(output: string): string[] {
    const errors: string[] = [];
    const lines = output.split('\n');

    for (const line of lines) {
      // 匹配 TypeScript 错误格式: file(line,col): error TS1234: message
      if (line.includes('error TS') || line.includes(': error')) {
        errors.push(line.trim());
      }
    }

    return errors;
  }

  /**
   * 解析 ESLint 输出
   */
  private parseEslintOutput(output: string): { errors: string[]; warnings: string[] } {
    const errors: string[] = [];
    const warnings: string[] = [];
    const lines = output.split('\n');

    for (const line of lines) {
      if (line.includes('Error') || line.includes('error')) {
        errors.push(line.trim());
      } else if (line.includes('Warning') || line.includes('warning')) {
        warnings.push(line.trim());
      }
    }

    return { errors, warnings };
  }

  /**
   * 解析测试输出
   */
  private parseTestOutput(output: string, code: number): TestResult {
    // 尝试解析 Jest/Vitest 格式
    const passMatch = output.match(/(\d+)\s+pass/i);
    const failMatch = output.match(/(\d+)\s+fail/i);
    const skipMatch = output.match(/(\d+)\s+skip/i);

    const passed = passMatch ? parseInt(passMatch[1], 10) : 0;
    const failed = failMatch ? parseInt(failMatch[1], 10) : 0;
    const skipped = skipMatch ? parseInt(skipMatch[1], 10) : 0;

    // 提取失败信息
    const failures: string[] = [];
    const failureMatch = output.match(/FAIL[\s\S]*?(?=\n\n|$)/g);

    if (failureMatch) {
      failures.push(...failureMatch.map((f) => f.trim()));
    }

    return {
      passed: code === 0,
      total: passed + failed + skipped,
      failed,
      skipped,
      failures,
    };
  }

  /**
   * 生成验证摘要
   */
  private generateSummary(
    typeCheck: CheckResult,
    lint: CheckResult,
    tests: TestResult
  ): string {
    const parts: string[] = [];

    // TypeScript
    if (typeCheck.passed) {
      parts.push('✅ TypeScript');
    } else {
      parts.push(`❌ TypeScript (${typeCheck.errors.length} errors)`);
    }

    // ESLint
    if (lint.passed) {
      parts.push('✅ ESLint');
    } else {
      parts.push(`❌ ESLint (${lint.errors.length} errors)`);
    }

    // Tests
    if (tests.passed) {
      parts.push(`✅ Tests (${tests.total - tests.failed}/${tests.total})`);
    } else {
      parts.push(`❌ Tests (${tests.failed} failed)`);
    }

    return parts.join(' | ');
  }

  /**
   * 检查文件是否存在
   */
  private async fileExists(filePath: string): Promise<boolean> {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * 检查是否存在 ESLint 配置
   */
  private async hasEslintConfig(worktreePath: string): Promise<boolean> {
    const configFiles = [
      '.eslintrc',
      '.eslintrc.js',
      '.eslintrc.json',
      '.eslintrc.yml',
      'eslint.config.js',
      'eslint.config.mjs',
    ];

    for (const file of configFiles) {
      if (await this.fileExists(path.join(worktreePath, file))) {
        return true;
      }
    }

    // 检查 package.json 中的 eslintConfig
    try {
      const pkgPath = path.join(worktreePath, 'package.json');
      const content = await fs.readFile(pkgPath, 'utf-8');
      const pkg = JSON.parse(content);
      return !!pkg.eslintConfig;
    } catch {
      return false;
    }
  }

  /**
   * 检查是否存在测试脚本
   */
  private async hasTestScript(worktreePath: string): Promise<boolean> {
    try {
      const pkgPath = path.join(worktreePath, 'package.json');
      const content = await fs.readFile(pkgPath, 'utf-8');
      const pkg = JSON.parse(content);
      return !!pkg.scripts?.test;
    } catch {
      return false;
    }
  }

  /**
   * 创建跳过的检查结果
   */
  private createSkippedCheckResult(): CheckResult {
    return {
      passed: true,
      errors: [],
      warnings: ['Check skipped'],
    };
  }

  /**
   * 创建跳过的测试结果
   */
  private createSkippedTestResult(): TestResult {
    return {
      passed: true,
      total: 0,
      failed: 0,
      skipped: 0,
      failures: [],
    };
  }
}
