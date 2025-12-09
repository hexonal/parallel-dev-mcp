/**
 * WorkerRunner - 程序化 Worker 执行器
 *
 * 在 Tmux 会话中作为独立进程运行
 * 使用 AgentExecutor 执行任务，通过 StatusReporter 报告状态
 *
 * @module parallel/worker/WorkerRunner
 */

import { simpleGit, SimpleGit } from 'simple-git';
import { Task, TaskResult } from '../types';
import { AgentExecutor, AgentExecutorConfig, ExecutionProgress } from './AgentExecutor';
import { StatusReporter, TaskResult as ReporterTaskResult } from './StatusReporter';
import { SocketClient } from '../communication/SocketClient';

/**
 * Git 配置
 */
export interface GitConfig {
  /** 自动提交 */
  autoCommit: boolean;
  /** 自动推送 */
  autoPush: boolean;
  /** 自动合并（创建 PR 并合并） */
  autoMerge: boolean;
  /** 分支名称（默认从 worktree 推断） */
  branchName?: string;
}

/**
 * WorkerRunner 配置
 */
export interface WorkerRunnerConfig {
  /** Worker ID */
  workerId: string;
  /** Master Socket.IO 端点 */
  masterEndpoint: string;
  /** Worktree 工作目录 */
  worktreePath: string;
  /** 要执行的任务 */
  task: Task;
  /** 执行器配置 */
  executorConfig?: Partial<AgentExecutorConfig>;
  /** Git 配置 */
  gitConfig?: GitConfig;
  /** Socket 认证 Token（可选） */
  socketToken?: string;
}

/**
 * 默认 Git 配置
 */
const DEFAULT_GIT_CONFIG: GitConfig = {
  autoCommit: true,
  autoPush: true,
  autoMerge: true,  // 默认启用自动合并，Worker 完成后通知 Master 执行合并
};

/**
 * WorkerRunner - 程序化 Worker 执行核心
 *
 * 职责：
 * 1. 连接 Master Socket.IO 服务
 * 2. 使用 AgentExecutor 执行任务
 * 3. 通过 StatusReporter 实时报告状态
 * 4. 任务完成后执行 Git 操作
 */
export class WorkerRunner {
  private config: WorkerRunnerConfig;
  private executor: AgentExecutor;
  private socketClient: SocketClient;
  private statusReporter: StatusReporter;
  private gitConfig: GitConfig;
  private git: SimpleGit;
  private startTime: number = 0;
  private messageCount: number = 0;

  constructor(config: WorkerRunnerConfig) {
    this.config = config;
    this.gitConfig = { ...DEFAULT_GIT_CONFIG, ...config.gitConfig };

    // 初始化 AgentExecutor
    this.executor = new AgentExecutor({
      permissionMode: 'acceptEdits',
      timeout: 600000,
      maxTurns: 50,
      loadProjectSettings: true,
      enableHooks: true,
      ...config.executorConfig,
    });

    // 初始化 SocketClient
    this.socketClient = new SocketClient({
      endpoint: config.masterEndpoint,
      workerId: config.workerId,
      token: config.socketToken,
    });

    // 初始化 StatusReporter
    this.statusReporter = new StatusReporter(
      this.socketClient,
      config.workerId,
      { autoStartHeartbeat: false }
    );

    // 初始化 Git
    this.git = simpleGit(config.worktreePath);
  }

  /**
   * 运行 Worker
   * 完整的生命周期：连接 → 执行 → 报告 → Git → 清理
   */
  async run(): Promise<TaskResult> {
    this.startTime = Date.now();
    this.log('info', `Starting worker ${this.config.workerId}`);
    this.log('info', `Task: ${this.config.task.title} (${this.config.task.id})`);
    this.log('info', `Worktree: ${this.config.worktreePath}`);

    try {
      // 1. 连接 Master
      await this.connectToMaster();

      // 2. 报告任务开始
      this.statusReporter.reportTaskStarted(this.config.task.id);
      this.log('info', 'Task started');

      // 3. 设置进度回调
      this.setupProgressCallback();

      // 4. 执行任务
      this.log('info', 'Executing task with AgentExecutor...');
      const result = await this.executor.execute(
        this.config.task,
        this.config.worktreePath
      );

      // 5. 处理结果
      if (result.success) {
        await this.handleSuccess(result);
      } else {
        await this.handleFailure(result);
      }

      return result;

    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      this.log('error', `Worker error: ${errorMsg}`);

      // 报告失败
      this.statusReporter.reportTaskFailed(this.config.task.id, errorMsg);

      return {
        success: false,
        error: errorMsg,
        duration: Date.now() - this.startTime,
        metadata: {
          executor: 'agent-sdk',
        },
      };

    } finally {
      // 6. 清理
      await this.cleanup();
    }
  }

  /**
   * 连接到 Master Socket.IO 服务
   */
  private async connectToMaster(): Promise<void> {
    this.log('info', `Connecting to Master: ${this.config.masterEndpoint}`);

    try {
      await this.socketClient.connect();
      this.statusReporter.startHeartbeat();
      this.statusReporter.reportReady();
      this.log('info', 'Connected to Master, heartbeat started');
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      this.log('warn', `Failed to connect to Master: ${errorMsg}`);
      // 继续执行，即使无法连接（离线模式）
    }
  }

  /**
   * 设置进度回调
   */
  private setupProgressCallback(): void {
    this.executor.setProgressCallback((progress: ExecutionProgress) => {
      this.messageCount++;

      // 基于消息数量估算进度（最多 90%）
      const percent = Math.min(90, this.messageCount * 3);

      // 截取进度消息
      const message = progress.content?.substring(0, 200) || progress.type;

      // 报告进度
      this.statusReporter.reportProgress(
        this.config.task.id,
        percent,
        message
      );

      // 日志
      if (progress.type === 'tool') {
        this.log('info', `Tool: ${progress.toolName}`);
      }
    });
  }

  /**
   * 处理任务成功
   */
  private async handleSuccess(result: TaskResult): Promise<void> {
    this.log('info', 'Task completed successfully');

    // 执行 Git 操作
    if (this.gitConfig.autoCommit) {
      try {
        await this.gitCommitAndPush();
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        this.log('warn', `Git operation failed: ${errorMsg}`);
        // Git 失败不影响任务结果
      }
    }

    // 报告完成
    const reportResult: ReporterTaskResult = {
      taskId: this.config.task.id,
      durationMs: result.duration || (Date.now() - this.startTime),
      output: result.output,
      metadata: result.metadata,
    };

    this.statusReporter.reportTaskCompleted(this.config.task.id, reportResult);
  }

  /**
   * 处理任务失败
   */
  private async handleFailure(result: TaskResult): Promise<void> {
    this.log('error', `Task failed: ${result.error}`);
    this.statusReporter.reportTaskFailed(
      this.config.task.id,
      result.error || 'Unknown error'
    );
  }

  /**
   * Git 提交和推送
   */
  private async gitCommitAndPush(): Promise<void> {
    this.log('info', 'Starting Git operations...');

    // 检查是否有更改
    const status = await this.git.status();
    if (status.files.length === 0) {
      this.log('info', 'No changes to commit');
      return;
    }

    // 1. 添加所有更改
    await this.git.add('.');
    this.log('info', `Staged ${status.files.length} files`);

    // 2. 提交
    const commitMsg = this.buildCommitMessage();
    await this.git.commit(commitMsg);
    this.log('info', `Committed: ${commitMsg}`);

    // 3. 推送（使用 --force 因为这是 Worker 专属分支，可能需要覆盖旧的远程分支）
    if (this.gitConfig.autoPush) {
      const branchName = this.gitConfig.branchName || await this.getCurrentBranch();
      await this.git.push('origin', branchName, ['--force']);
      this.log('info', `Pushed to origin/${branchName}`);
    }

    // 4. 请求 Master 执行合并（可选）
    if (this.gitConfig.autoMerge) {
      await this.requestMerge();
    }
  }

  /**
   * 构建提交消息
   */
  private buildCommitMessage(): string {
    const task = this.config.task;
    const type = this.inferCommitType(task);
    return `${type}(${task.id}): ${task.title}\n\n🤖 Generated by ParallelDev Worker`;
  }

  /**
   * 推断提交类型
   */
  private inferCommitType(task: Task): string {
    const title = task.title.toLowerCase();
    const description = task.description.toLowerCase();

    if (title.includes('fix') || description.includes('bug')) {
      return 'fix';
    }
    if (title.includes('test') || description.includes('test')) {
      return 'test';
    }
    if (title.includes('doc') || description.includes('document')) {
      return 'docs';
    }
    if (title.includes('refactor')) {
      return 'refactor';
    }
    return 'feat';
  }

  /**
   * 获取当前分支名
   */
  private async getCurrentBranch(): Promise<string> {
    const branch = await this.git.branch();
    return branch.current;
  }

  /**
   * 通知 Master 执行合并
   * Worker 在 worktree 中无法直接合并到主分支，需要通知 Master 来执行
   */
  private async requestMerge(): Promise<void> {
    const branchName = this.gitConfig.branchName || await this.getCurrentBranch();

    this.log('info', `Requesting merge for ${branchName}...`);

    // 通过 Socket 通知 Master 执行合并
    this.socketClient.emit('worker:merge_request', {
      workerId: this.config.workerId,
      taskId: this.config.task.id,
      branchName,
      timestamp: new Date().toISOString(),
    });

    // 等待消息发送完成，避免 fire-and-forget 导致消息丢失
    await new Promise(resolve => setTimeout(resolve, 500));

    this.log('info', `Merge request sent for ${branchName}`);
  }

  /**
   * 清理资源
   */
  private async cleanup(): Promise<void> {
    this.log('info', 'Cleaning up...');

    try {
      this.statusReporter.stopHeartbeat();

      // 等待一小段时间确保最后的消息（如 task_completed）已发送
      await new Promise((resolve) => setTimeout(resolve, 500));

      this.socketClient.disconnect();
    } catch {
      // 忽略清理错误
    }

    this.log('info', `Worker ${this.config.workerId} finished`);
  }

  /**
   * 日志输出
   */
  private log(level: 'info' | 'warn' | 'error', message: string): void {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [WorkerRunner] [${level.toUpperCase()}]`;

    switch (level) {
      case 'error':
        console.error(`${prefix} ${message}`);
        break;
      case 'warn':
        console.warn(`${prefix} ${message}`);
        break;
      default:
        console.log(`${prefix} ${message}`);
    }

    // 同时通过 StatusReporter 发送日志
    if (this.socketClient.isConnected()) {
      this.statusReporter.reportLog(level, message);
    }
  }

  /**
   * 取消执行
   */
  async cancel(): Promise<void> {
    this.log('info', 'Cancelling task...');
    await this.executor.cancel();
  }

  /**
   * 检查是否正在执行
   */
  isRunning(): boolean {
    return this.executor.isRunning();
  }

  /**
   * 获取配置
   */
  getConfig(): WorkerRunnerConfig {
    return { ...this.config };
  }
}
