/**
 * Worker Claude Runner - 基于 Happy SDK 模式的 Claude Code 执行器
 * @module parallel/worker/WorkerClaudeRunner
 *
 * 参考 happy-cli/src/claude/sdk/query.ts 实现
 * 核心：通过 stdin/stdout JSON 流式交互，而非生成脚本执行
 */

import { spawn, ChildProcessWithoutNullStreams } from 'node:child_process';
import { createInterface } from 'node:readline';
import { existsSync } from 'node:fs';
import { EventEmitter } from 'eventemitter3';
import { Writable } from 'node:stream';

/**
 * SDK 消息类型（与 Claude Code 输出格式对齐）
 */
export interface SDKMessage {
  type: 'system' | 'user' | 'assistant' | 'result';
  subtype?: string;
  session_id?: string;
  message?: {
    role: string;
    content: string | Array<{ type: string; text?: string; [key: string]: unknown }>;
  };
  [key: string]: unknown;
}

/**
 * 用户消息结构
 */
export interface SDKUserMessage {
  type: 'user';
  message: {
    role: 'user';
    content: string;
  };
}

/**
 * Runner 配置
 */
export interface WorkerClaudeRunnerConfig {
  /** 工作目录 */
  workingDir: string;
  /** 权限模式 */
  permissionMode?: 'default' | 'acceptEdits' | 'bypassPermissions';
  /** Claude 模型 */
  model?: string;
  /** 超时时间（毫秒） */
  timeout?: number;
  /** 恢复会话 ID */
  sessionId?: string;
  /** 最大对话轮数 */
  maxTurns?: number;
  /** 允许的工具 */
  allowedTools?: string[];
  /** 禁止的工具 */
  disallowedTools?: string[];
  /** 自定义系统提示 */
  systemPrompt?: string;
  /** 追加系统提示 */
  appendSystemPrompt?: string;
}

/**
 * Runner 事件类型
 */
export interface WorkerClaudeRunnerEvents {
  message: (msg: SDKMessage) => void;
  ready: () => void;
  error: (error: Error) => void;
  exit: (code: number | null) => void;
}

/**
 * 获取 Claude Code 可执行路径
 */
function getClaudeCodePath(): string {
  // 尝试常见安装路径（按优先级排序）
  const possiblePaths = [
    // Claude Code 本地安装（推荐）
    `${process.env.HOME}/.local/bin/claude`,
    // npm global (macOS/Linux)
    '/usr/local/bin/claude',
    // Homebrew
    '/opt/homebrew/bin/claude',
    // npm global in user dir
    `${process.env.HOME}/.npm-global/bin/claude`,
  ];

  for (const p of possiblePaths) {
    if (existsSync(p)) {
      return p;
    }
  }

  // 默认使用 claude（依赖 PATH）
  return 'claude';
}

/**
 * WorkerClaudeRunner - 基于 Happy SDK 方式的 Claude Code 执行器
 *
 * 直接 spawn Claude Code CLI，通过 stdin 发送消息，stdout 接收响应
 * 支持持续对话，而非一次性脚本执行
 */
export class WorkerClaudeRunner extends EventEmitter<WorkerClaudeRunnerEvents> {
  private config: WorkerClaudeRunnerConfig;
  private child: ChildProcessWithoutNullStreams | null = null;
  private childStdin: Writable | null = null;
  private sessionId: string | null = null;
  private isRunning = false;
  private processExitPromise: Promise<void> | null = null;
  private collectedOutput: string[] = [];
  private lastResult: SDKMessage | null = null;

  constructor(config: WorkerClaudeRunnerConfig) {
    super();
    this.config = config;
    this.sessionId = config.sessionId ?? null;
  }

  /**
   * 启动 Claude Code 进程
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      throw new Error('Runner is already running');
    }

    // 构建命令参数
    const args = this.buildArgs();

    // 获取 Claude Code 可执行路径
    const claudePath = getClaudeCodePath();

    // 设置环境变量
    const env = {
      ...process.env,
      CLAUDE_CODE_ENTRYPOINT: 'paralleldev-worker'
    };

    // Spawn 进程
    this.child = spawn(claudePath, args, {
      cwd: this.config.workingDir,
      stdio: ['pipe', 'pipe', 'pipe'],
      env
    }) as ChildProcessWithoutNullStreams;

    this.childStdin = this.child.stdin;
    this.isRunning = true;

    // 设置进程退出 Promise
    this.processExitPromise = new Promise((resolve) => {
      this.child!.on('close', (code) => {
        this.isRunning = false;
        this.emit('exit', code);
        resolve();
      });
    });

    // 设置消息读取
    this.setupMessageReader();

    // 处理进程错误
    this.child.on('error', (error) => {
      this.isRunning = false;
      this.emit('error', error);
    });

    // 处理 stderr
    this.child.stderr.on('data', (data) => {
      const message = data.toString();
      // 检查登录错误
      if (message.includes('Please run /login') || message.includes('403')) {
        this.emit('error', new Error(`Claude Code 认证失败: ${message}`));
      }
    });
  }

  /**
   * 发送用户消息
   */
  sendMessage(content: string): void {
    if (!this.childStdin || !this.isRunning) {
      throw new Error('Runner is not running');
    }

    const message: SDKUserMessage = {
      type: 'user',
      message: {
        role: 'user',
        content
      }
    };

    this.childStdin.write(JSON.stringify(message) + '\n');
  }

  /**
   * 发送中断请求
   */
  async interrupt(): Promise<void> {
    if (!this.childStdin || !this.isRunning) {
      throw new Error('Runner is not running');
    }

    const request = {
      request_id: Math.random().toString(36).substring(2, 15),
      type: 'control_request',
      request: {
        subtype: 'interrupt'
      }
    };

    this.childStdin.write(JSON.stringify(request) + '\n');
  }

  /**
   * 停止进程
   */
  stop(): void {
    if (this.child && !this.child.killed) {
      this.child.kill('SIGTERM');
    }
    this.isRunning = false;
  }

  /**
   * 强制终止进程
   */
  kill(): void {
    if (this.child && !this.child.killed) {
      this.child.kill('SIGKILL');
    }
    this.isRunning = false;
  }

  /**
   * 等待进程退出
   */
  async waitForExit(): Promise<void> {
    if (this.processExitPromise) {
      await this.processExitPromise;
    }
  }

  /**
   * 获取当前会话 ID
   */
  getSessionId(): string | null {
    return this.sessionId;
  }

  /**
   * 检查是否运行中
   */
  isActive(): boolean {
    return this.isRunning;
  }

  /**
   * 获取收集的输出
   */
  getCollectedOutput(): string[] {
    return [...this.collectedOutput];
  }

  /**
   * 获取最后的结果消息
   */
  getLastResult(): SDKMessage | null {
    return this.lastResult;
  }

  /**
   * 清空收集的输出
   */
  clearOutput(): void {
    this.collectedOutput = [];
    this.lastResult = null;
  }

  /**
   * 构建 CLI 参数
   */
  private buildArgs(): string[] {
    const args = [
      '--output-format', 'stream-json',
      '--input-format', 'stream-json',
      '--verbose'
    ];

    // 权限模式
    if (this.config.permissionMode) {
      args.push('--permission-mode', this.config.permissionMode);
    }

    // 模型
    if (this.config.model) {
      args.push('--model', this.config.model);
    }

    // 最大轮数
    if (this.config.maxTurns) {
      args.push('--max-turns', this.config.maxTurns.toString());
    }

    // 允许的工具
    if (this.config.allowedTools && this.config.allowedTools.length > 0) {
      args.push('--allowedTools', this.config.allowedTools.join(','));
    }

    // 禁止的工具
    if (this.config.disallowedTools && this.config.disallowedTools.length > 0) {
      args.push('--disallowedTools', this.config.disallowedTools.join(','));
    }

    // 自定义系统提示
    if (this.config.systemPrompt) {
      args.push('--system-prompt', this.config.systemPrompt);
    }

    // 追加系统提示
    if (this.config.appendSystemPrompt) {
      args.push('--append-system-prompt', this.config.appendSystemPrompt);
    }

    // 恢复会话
    if (this.sessionId) {
      args.push('--resume', this.sessionId);
    }

    return args;
  }

  /**
   * 设置消息读取器
   */
  private setupMessageReader(): void {
    if (!this.child) return;

    const rl = createInterface({ input: this.child.stdout });

    rl.on('line', (line) => {
      if (!line.trim()) return;

      try {
        const message = JSON.parse(line) as SDKMessage;

        // 处理系统初始化消息
        if (message.type === 'system' && message.subtype === 'init') {
          if (message.session_id) {
            this.sessionId = message.session_id;
          }
          this.emit('ready');
        }

        // 收集 assistant 消息内容
        if (message.type === 'assistant' && message.message) {
          const content = this.extractTextContent(message);
          if (content) {
            this.collectedOutput.push(content);
          }
        }

        // 处理结果消息
        if (message.type === 'result') {
          this.lastResult = message;
        }

        // 发出消息事件
        this.emit('message', message);
      } catch {
        // JSON 解析失败，可能是普通日志输出
        if (process.env.DEBUG) {
          console.log('[WorkerClaudeRunner non-json]', line);
        }
      }
    });

    rl.on('close', () => {
      this.isRunning = false;
    });
  }

  /**
   * 提取文本内容
   */
  private extractTextContent(message: SDKMessage): string | undefined {
    if (message.type !== 'assistant' || !message.message) {
      return undefined;
    }

    const content = message.message.content;
    if (typeof content === 'string') {
      return content;
    }

    if (Array.isArray(content)) {
      const textParts: string[] = [];
      for (const block of content) {
        if (block.type === 'text' && typeof block.text === 'string') {
          textParts.push(block.text);
        }
      }
      return textParts.length > 0 ? textParts.join('\n') : undefined;
    }

    return undefined;
  }
}

/**
 * 创建并启动 Runner 的便捷函数
 */
export async function createWorkerRunner(
  config: WorkerClaudeRunnerConfig
): Promise<WorkerClaudeRunner> {
  const runner = new WorkerClaudeRunner(config);
  await runner.start();
  return runner;
}
