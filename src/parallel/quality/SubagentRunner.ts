/**
 * SubagentRunner - Subagent 运行器
 *
 * 负责调用 Claude Code Subagent 执行质量检查和冲突解决
 */

import { spawn } from 'child_process';
import * as path from 'path';
import { EventEmitter } from 'events';

/**
 * Subagent 执行结果
 */
export interface SubagentResult {
  success: boolean;
  output: string;
  error?: string;
  duration: number;
}

/**
 * 质量检查结果
 */
export interface QualityCheckResult {
  passed: boolean;
  typeCheck: {
    passed: boolean;
    errors: string[];
  };
  lint: {
    passed: boolean;
    errors: string[];
  };
  tests: {
    passed: boolean;
    failures: string[];
  };
  summary: string;
}

/**
 * 冲突信息
 */
export interface ConflictInfo {
  file: string;
  type: 'content' | 'rename' | 'delete';
  severity: 'low' | 'medium' | 'high';
  description: string;
}

/**
 * 冲突解决结果
 */
export interface ResolveResult {
  success: boolean;
  resolved: ConflictInfo[];
  unresolved: ConflictInfo[];
  needsHumanReview: ConflictInfo[];
  summary: string;
}

/**
 * Subagent 运行器配置
 */
export interface SubagentRunnerConfig {
  projectRoot: string;
  agentsDir?: string;
  timeout?: number;
  model?: 'sonnet' | 'haiku';
}

/**
 * SubagentRunner 类
 *
 * 使用 Claude Code Headless 模式运行 Subagent
 */
export class SubagentRunner extends EventEmitter {
  private projectRoot: string;
  private agentsDir: string;
  private timeout: number;
  private defaultModel: 'sonnet' | 'haiku';

  constructor(config: SubagentRunnerConfig) {
    super();
    this.projectRoot = config.projectRoot;
    this.agentsDir = config.agentsDir || path.join(config.projectRoot, 'paralleldev-plugin/agents');
    this.timeout = config.timeout || 300000;
    this.defaultModel = config.model || 'sonnet';
  }

  /**
   * 运行 Subagent
   *
   * @param agentName Agent 名称
   * @param prompt 执行提示
   * @param model 模型选择
   */
  async run(
    agentName: string,
    prompt: string,
    model?: 'sonnet' | 'haiku'
  ): Promise<SubagentResult> {
    const startTime = Date.now();
    const selectedModel = model || this.defaultModel;

    // 构建 agent 文件路径
    const agentFile = path.join(this.agentsDir, `${agentName}.md`);

    // 构建完整 prompt（包含 agent 指令）
    const fullPrompt = `按照 ${agentFile} 中的指令执行以下任务：\n\n${prompt}`;

    try {
      const output = await this.executeHeadless(fullPrompt, selectedModel);

      return {
        success: true,
        output,
        duration: Date.now() - startTime,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

      return {
        success: false,
        output: '',
        error: errorMessage,
        duration: Date.now() - startTime,
      };
    }
  }

  /**
   * 运行质量检查 Agent
   *
   * @param worktreePath Worktree 路径
   */
  async runQualityGate(worktreePath: string): Promise<QualityCheckResult> {
    const prompt = `
在 ${worktreePath} 目录下执行质量检查：

1. TypeScript 类型检查 (tsc --noEmit)
2. ESLint 检查 (eslint .)
3. 单元测试 (npm test)

输出 JSON 格式结果：
{
  "passed": boolean,
  "typeCheck": { "passed": boolean, "errors": string[] },
  "lint": { "passed": boolean, "errors": string[] },
  "tests": { "passed": boolean, "failures": string[] },
  "summary": string
}
`;

    const result = await this.run('quality-gate', prompt, 'haiku');

    if (!result.success) {
      return this.createFailedQualityResult(result.error || 'Unknown error');
    }

    try {
      // 尝试解析 JSON 结果
      const jsonMatch = result.output.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]) as QualityCheckResult;
      }

      // 解析失败，返回默认结果
      return this.createFailedQualityResult('Failed to parse quality check result');
    } catch {
      return this.createFailedQualityResult('Failed to parse quality check result');
    }
  }

  /**
   * 运行冲突解决 Agent
   *
   * @param worktreePath Worktree 路径
   * @param conflicts 冲突信息列表
   */
  async runConflictResolver(
    worktreePath: string,
    conflicts: ConflictInfo[]
  ): Promise<ResolveResult> {
    const conflictList = conflicts
      .map((c, i) => `${i + 1}. ${c.file} (${c.type}, ${c.severity}): ${c.description}`)
      .join('\n');

    const prompt = `
在 ${worktreePath} 目录下解决以下冲突：

${conflictList}

按照分层策略解决：
- Level 1: 自动解决（lockfiles, 格式化）
- Level 2: AI 辅助解决
- Level 3: 标记需要人工介入

输出 JSON 格式结果：
{
  "success": boolean,
  "resolved": [{ "file": string, "type": string, "severity": string, "description": string }],
  "unresolved": [...],
  "needsHumanReview": [...],
  "summary": string
}
`;

    const result = await this.run('conflict-resolver', prompt, 'sonnet');

    if (!result.success) {
      return this.createFailedResolveResult(conflicts, result.error || 'Unknown error');
    }

    try {
      const jsonMatch = result.output.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]) as ResolveResult;
      }

      return this.createFailedResolveResult(conflicts, 'Failed to parse resolve result');
    } catch {
      return this.createFailedResolveResult(conflicts, 'Failed to parse resolve result');
    }
  }

  /**
   * 执行 Claude Code Headless 命令
   */
  private executeHeadless(prompt: string, model: 'sonnet' | 'haiku'): Promise<string> {
    return new Promise((resolve, reject) => {
      const modelArg = model === 'haiku' ? '--model haiku' : '';
      const args = [
        '--dangerously-skip-permissions',
        '-p',
        prompt,
      ];

      if (model === 'haiku') {
        args.unshift('--model', 'haiku');
      }

      const child = spawn('claude', args, {
        cwd: this.projectRoot,
        timeout: this.timeout,
        shell: true,
      });

      let stdout = '';
      let stderr = '';

      child.stdout?.on('data', (data) => {
        stdout += data.toString();
        this.emit('output', data.toString());
      });

      child.stderr?.on('data', (data) => {
        stderr += data.toString();
        this.emit('error', data.toString());
      });

      child.on('close', (code) => {
        if (code === 0) {
          resolve(stdout);
        } else {
          reject(new Error(`Process exited with code ${code}: ${stderr}`));
        }
      });

      child.on('error', (err) => {
        reject(err);
      });
    });
  }

  /**
   * 创建失败的质量检查结果
   */
  private createFailedQualityResult(error: string): QualityCheckResult {
    return {
      passed: false,
      typeCheck: { passed: false, errors: [error] },
      lint: { passed: false, errors: [] },
      tests: { passed: false, failures: [] },
      summary: `Quality check failed: ${error}`,
    };
  }

  /**
   * 创建失败的冲突解决结果
   */
  private createFailedResolveResult(conflicts: ConflictInfo[], error: string): ResolveResult {
    return {
      success: false,
      resolved: [],
      unresolved: conflicts,
      needsHumanReview: [],
      summary: `Conflict resolution failed: ${error}`,
    };
  }
}
