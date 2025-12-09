/**
 * REPLShell - 持久交互式命令行界面
 *
 * 类似 Claude Code 的交互式 REPL：
 * - Master 主会话始终打开
 * - 实时显示 Worker 状态
 * - 支持命令输入和执行
 */

import * as readline from 'readline';
import chalk from 'chalk';
import { EventEmitter } from 'events';
import { MasterServer } from './MasterServer';
import {
  StateManager,
  TaskManager,
  TmuxController,
  loadConfig,
  PDEV_PATHS
} from '../parallel';
import { ParallelDevConfig, Worker } from '../parallel/types';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Worker 状态信息
 */
interface WorkerState {
  id: string;
  status: 'idle' | 'busy' | 'error' | 'offline';
  taskId?: string;
  progress?: number;
  lastHeartbeat: number;
}

/**
 * REPL Shell 配置
 */
export interface REPLShellConfig {
  /** 项目根目录 */
  projectRoot: string;
  /** Socket 端口 */
  socketPort?: number;
  /** 欢迎信息 */
  showWelcome?: boolean;
}

/**
 * REPLShell - 持久交互式命令行
 */
export class REPLShell extends EventEmitter {
  private rl: readline.Interface | null = null;
  private masterServer: MasterServer;
  private stateManager: StateManager;
  private taskManager: TaskManager | null = null;
  private tmuxController: TmuxController;
  private config: ParallelDevConfig | null = null;
  private projectRoot: string;
  private isRunning: boolean = false;

  // Worker 状态追踪
  private workers: Map<string, WorkerState> = new Map();

  // 命令历史
  private history: string[] = [];

  constructor(options: REPLShellConfig) {
    super();
    this.projectRoot = options.projectRoot;
    this.stateManager = new StateManager(this.projectRoot);
    this.tmuxController = new TmuxController();
    this.masterServer = new MasterServer({
      port: options.socketPort || 3847
    });

    // 监听 Worker 事件
    this.setupWorkerEventListeners();
  }

  /**
   * 启动 REPL
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      return;
    }

    this.isRunning = true;

    // 1. 加载配置
    try {
      this.config = await loadConfig(this.projectRoot);
      this.taskManager = new TaskManager(this.projectRoot, this.config);
    } catch {
      // 配置文件不存在，使用默认值
      this.config = null;
    }

    // 2. 启动 Socket 服务器
    await this.masterServer.start();

    // 3. 加载现有状态
    await this.loadExistingState();

    // 4. 显示欢迎信息
    this.showWelcome();

    // 5. 启动命令行循环
    this.startReadline();

    // 6. 发出启动事件
    this.emit('started');
  }

  /**
   * 停止 REPL
   */
  async stop(): Promise<void> {
    if (!this.isRunning) {
      return;
    }

    this.isRunning = false;

    // 关闭 readline
    if (this.rl) {
      this.rl.close();
      this.rl = null;
    }

    // 停止 Socket 服务器
    await this.masterServer.stop();

    // 保存状态
    await this.stateManager.saveState(this.stateManager.getState());

    this.emit('stopped');
  }

  /**
   * 显示欢迎信息
   */
  private showWelcome(): void {
    console.log();
    console.log(chalk.cyan('╔════════════════════════════════════════════════════════════╗'));
    console.log(chalk.cyan('║') + chalk.bold.white('         pdev - ParallelDev 交互式控制台                  ') + chalk.cyan('║'));
    console.log(chalk.cyan('╚════════════════════════════════════════════════════════════╝'));
    console.log();
    console.log(chalk.gray('  输入 help 查看可用命令，exit 退出'));
    console.log(chalk.gray(`  Socket 服务端口: ${this.masterServer.getPort()}`));
    console.log();

    // 显示当前状态摘要
    this.showStatusSummary();
  }

  /**
   * 显示状态摘要
   */
  private showStatusSummary(): void {
    const workerCount = this.workers.size;
    const busyWorkers = Array.from(this.workers.values()).filter(w => w.status === 'busy').length;

    if (workerCount === 0) {
      console.log(chalk.yellow('  当前没有连接的 Worker'));
    } else {
      console.log(chalk.green(`  已连接 Worker: ${workerCount} (${busyWorkers} 忙碌)`));
    }
    console.log();
  }

  /**
   * 启动 readline 循环
   */
  private startReadline(): void {
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      prompt: chalk.cyan('pdev> '),
      historySize: 100
    });

    this.rl.prompt();

    this.rl.on('line', async (line) => {
      const cmd = line.trim();

      if (cmd) {
        this.history.push(cmd);
        await this.handleCommand(cmd);
      }

      if (this.isRunning && this.rl) {
        this.rl.prompt();
      }
    });

    this.rl.on('close', () => {
      if (this.isRunning) {
        this.stop();
      }
    });
  }

  /**
   * 处理命令
   */
  private async handleCommand(input: string): Promise<void> {
    const parts = input.split(/\s+/);
    const cmd = parts[0].toLowerCase();
    const args = parts.slice(1);

    try {
      switch (cmd) {
        case 'help':
        case '?':
          this.showHelp();
          break;

        case 'status':
          await this.cmdStatus();
          break;

        case 'workers':
          this.cmdWorkers();
          break;

        case 'tasks':
          await this.cmdTasks();
          break;

        case 'run':
          await this.cmdRun(args);
          break;

        case 'stop':
          await this.cmdStop();
          break;

        case 'logs':
          await this.cmdLogs(args);
          break;

        case 'attach':
          await this.cmdAttach(args);
          break;

        case 'clear':
          console.clear();
          break;

        case 'exit':
        case 'quit':
        case 'q':
          console.log(chalk.yellow('再见!'));
          await this.stop();
          process.exit(0);
          break;

        default:
          console.log(chalk.red(`未知命令: ${cmd}`));
          console.log(chalk.gray('输入 help 查看可用命令'));
      }
    } catch (error) {
      console.log(chalk.red(`命令执行失败: ${error instanceof Error ? error.message : error}`));
    }
  }

  /**
   * 显示帮助
   */
  private showHelp(): void {
    console.log();
    console.log(chalk.bold('可用命令:'));
    console.log();
    console.log(chalk.cyan('  status') + '           显示当前系统状态');
    console.log(chalk.cyan('  workers') + '          列出所有 Worker');
    console.log(chalk.cyan('  tasks') + '            列出任务');
    console.log(chalk.cyan('  run [--prd <file>]') + '  启动任务执行');
    console.log(chalk.cyan('  stop') + '             停止所有任务');
    console.log(chalk.cyan('  logs [worker-id]') + '  查看 Worker 日志');
    console.log(chalk.cyan('  attach <worker-id>') + ' 连接到 Worker tmux 会话');
    console.log(chalk.cyan('  clear') + '            清屏');
    console.log(chalk.cyan('  exit') + '             退出');
    console.log();
  }

  /**
   * 命令: status
   */
  private async cmdStatus(): Promise<void> {
    console.log();
    console.log(chalk.bold('系统状态'));
    console.log(chalk.gray('─'.repeat(50)));

    // Master 状态
    const workerStats = this.masterServer.getWorkerStats();
    console.log(chalk.cyan('Master:'));
    console.log(`  Socket 端口: ${this.masterServer.getPort()}`);
    console.log(`  连接 Worker: ${workerStats.total}`);

    // 从 state.json 读取状态
    const state = await this.stateManager.loadState();
    if (state) {
      console.log(`  阶段: ${state.currentPhase}`);
      console.log(`  开始时间: ${state.startedAt || 'N/A'}`);
    }

    // Worker 状态
    console.log();
    console.log(chalk.cyan('Workers:'));
    if (this.workers.size === 0) {
      console.log(chalk.yellow('  没有连接的 Worker'));
    } else {
      for (const [id, worker] of this.workers) {
        const statusIcon = this.getStatusIcon(worker.status);
        const taskInfo = worker.taskId ? ` [${worker.taskId}]` : '';
        const progress = worker.progress !== undefined ? ` ${worker.progress}%` : '';
        console.log(`  ${statusIcon} ${id}: ${worker.status}${taskInfo}${progress}`);
      }
    }

    console.log();
  }

  /**
   * 命令: workers
   */
  private cmdWorkers(): void {
    console.log();
    console.log(chalk.bold('Worker 列表'));
    console.log(chalk.gray('─'.repeat(50)));

    const connectedWorkers = this.masterServer.getWorkers();

    if (connectedWorkers.size === 0) {
      console.log(chalk.yellow('没有连接的 Worker'));
      console.log();
      return;
    }

    console.log(chalk.gray('ID'.padEnd(20) + 'Status'.padEnd(15) + 'Task'.padEnd(15) + 'Progress'));
    console.log(chalk.gray('─'.repeat(60)));

    for (const [workerId, serverWorker] of connectedWorkers) {
      const localWorker = this.workers.get(workerId);
      const status = (serverWorker.status || localWorker?.status || 'idle').padEnd(15);
      const task = (serverWorker.taskId || localWorker?.taskId || '-').padEnd(15);
      const progress = serverWorker.progress !== undefined
        ? `${serverWorker.progress}%`
        : (localWorker?.progress !== undefined ? `${localWorker.progress}%` : '-');

      console.log(`${workerId.padEnd(20)}${status}${task}${progress}`);
    }

    console.log();
  }

  /**
   * 命令: tasks
   */
  private async cmdTasks(): Promise<void> {
    if (!this.taskManager) {
      console.log(chalk.yellow('任务管理器未初始化，请先运行 pdev init'));
      return;
    }

    console.log();
    console.log(chalk.bold('任务列表'));
    console.log(chalk.gray('─'.repeat(50)));

    try {
      const tasks = await this.taskManager.loadTasks();

      if (tasks.length === 0) {
        console.log(chalk.yellow('没有任务'));
        console.log();
        return;
      }

      const stats = this.taskManager.getStats();
      console.log(chalk.gray(`总计: ${stats.total} | 待执行: ${stats.pending} | 进行中: ${stats.running} | 完成: ${stats.completed} | 失败: ${stats.failed}`));
      console.log();

      for (const task of tasks.slice(0, 10)) {
        const statusIcon = this.getTaskStatusIcon(task.status);
        console.log(`  ${statusIcon} [${task.id}] ${task.title}`);
      }

      if (tasks.length > 10) {
        console.log(chalk.gray(`  ... 还有 ${tasks.length - 10} 个任务`));
      }
    } catch (error) {
      console.log(chalk.red(`加载任务失败: ${error}`));
    }

    console.log();
  }

  /**
   * 命令: run
   */
  private async cmdRun(args: string[]): Promise<void> {
    // 检查是否已初始化
    const pdevPath = path.join(this.projectRoot, PDEV_PATHS.root);
    if (!fs.existsSync(pdevPath)) {
      console.log(chalk.red('项目未初始化，请先运行 pdev init'));
      return;
    }

    // 解析参数
    let prdPath: string | null = null;
    for (let i = 0; i < args.length; i++) {
      if (args[i] === '--prd' && args[i + 1]) {
        prdPath = args[i + 1];
        break;
      }
    }

    console.log(chalk.blue('启动任务执行...'));

    // TODO: 集成 MasterOrchestrator 启动任务
    console.log(chalk.yellow('功能开发中...'));
  }

  /**
   * 命令: stop
   */
  private async cmdStop(): Promise<void> {
    console.log(chalk.yellow('停止所有任务...'));

    // 更新状态
    this.stateManager.updateState({
      currentPhase: 'idle',
      updatedAt: new Date().toISOString()
    });

    await this.stateManager.saveState(this.stateManager.getState());

    // 通知所有 Worker 停止
    this.masterServer.broadcast('stop', {});

    console.log(chalk.green('已停止'));
  }

  /**
   * 命令: logs
   */
  private async cmdLogs(args: string[]): Promise<void> {
    const workerId = args[0];

    if (!workerId) {
      console.log(chalk.yellow('用法: logs <worker-id>'));
      console.log(chalk.gray('使用 workers 命令查看可用的 Worker'));
      return;
    }

    // 获取 Worker 对应的 tmux 会话
    const sessionName = this.tmuxController.getSessionName(workerId);

    if (!this.tmuxController.sessionExists(sessionName)) {
      console.log(chalk.red(`Worker ${workerId} 的 tmux 会话不存在`));
      return;
    }

    console.log(chalk.bold(`Worker ${workerId} 日志 (最近 50 行):`));
    console.log(chalk.gray('─'.repeat(50)));

    const output = await this.tmuxController.captureOutput(sessionName, 50);
    console.log(output || chalk.gray('(无输出)'));
  }

  /**
   * 命令: attach
   */
  private async cmdAttach(args: string[]): Promise<void> {
    const workerId = args[0];

    if (!workerId) {
      console.log(chalk.yellow('用法: attach <worker-id>'));
      console.log(chalk.gray('使用 workers 命令查看可用的 Worker'));
      return;
    }

    const sessionName = this.tmuxController.getSessionName(workerId);

    if (!this.tmuxController.sessionExists(sessionName)) {
      console.log(chalk.red(`Worker ${workerId} 的 tmux 会话不存在`));
      return;
    }

    console.log(chalk.cyan(`连接到 tmux 会话: ${sessionName}`));
    console.log(chalk.gray('按 Ctrl+B D 返回 pdev'));

    // 暂停 readline，让用户与 tmux 交互
    if (this.rl) {
      this.rl.pause();
    }

    // 使用 spawn 而不是 exec，让用户可以交互
    const { spawn } = await import('child_process');
    const tmux = spawn('tmux', ['attach', '-t', sessionName], {
      stdio: 'inherit'
    });

    await new Promise<void>((resolve) => {
      tmux.on('close', () => {
        resolve();
      });
    });

    // 恢复 readline
    if (this.rl) {
      this.rl.resume();
      this.rl.prompt();
    }
  }

  /**
   * 加载现有状态
   */
  private async loadExistingState(): Promise<void> {
    try {
      const state = await this.stateManager.loadState();

      if (state && state.workers) {
        for (const worker of state.workers) {
          this.workers.set(worker.id, {
            id: worker.id,
            status: worker.status as WorkerState['status'],
            taskId: worker.currentTaskId,
            lastHeartbeat: Date.now()
          });
        }
      }
    } catch {
      // 忽略加载错误
    }
  }

  /**
   * 设置 Worker 事件监听
   */
  private setupWorkerEventListeners(): void {
    // Worker 连接
    this.masterServer.on('worker:connected', ({ workerId }) => {
      this.workers.set(workerId, {
        id: workerId,
        status: 'idle',
        lastHeartbeat: Date.now()
      });
      this.printEvent(chalk.green(`Worker ${workerId} 已连接`));
    });

    // Worker 断开
    this.masterServer.on('worker:disconnected', ({ workerId }) => {
      const worker = this.workers.get(workerId);
      if (worker) {
        worker.status = 'offline';
      }
      this.printEvent(chalk.yellow(`Worker ${workerId} 已断开`));
    });

    // 心跳
    this.masterServer.on('worker:heartbeat', ({ workerId }) => {
      const worker = this.workers.get(workerId);
      if (worker) {
        worker.lastHeartbeat = Date.now();
      }
    });

    // 任务开始
    this.masterServer.on('worker:task_started', ({ workerId, taskId }) => {
      const worker = this.workers.get(workerId);
      if (worker) {
        worker.status = 'busy';
        worker.taskId = taskId;
        worker.progress = 0;
      }
      this.printEvent(chalk.blue(`Worker ${workerId} 开始任务 ${taskId}`));
    });

    // 任务完成
    this.masterServer.on('worker:task_completed', ({ workerId, taskId }) => {
      const worker = this.workers.get(workerId);
      if (worker) {
        worker.status = 'idle';
        worker.taskId = undefined;
        worker.progress = undefined;
      }
      this.printEvent(chalk.green(`Worker ${workerId} 完成任务 ${taskId}`));
    });

    // 任务失败
    this.masterServer.on('worker:task_failed', ({ workerId, taskId, error }) => {
      const worker = this.workers.get(workerId);
      if (worker) {
        worker.status = 'error';
      }
      this.printEvent(chalk.red(`Worker ${workerId} 任务 ${taskId} 失败: ${error}`));
    });

    // 状态更新
    this.masterServer.on('worker:status_update', ({ workerId, status, progress }) => {
      const worker = this.workers.get(workerId);
      if (worker) {
        if (status) worker.status = status;
        if (progress !== undefined) worker.progress = progress;
      }
    });
  }

  /**
   * 打印事件（不打断命令提示符）
   */
  private printEvent(message: string): void {
    // 清除当前行，打印事件，重新显示提示符
    if (this.rl) {
      readline.clearLine(process.stdout, 0);
      readline.cursorTo(process.stdout, 0);
      console.log(chalk.gray(`[${new Date().toLocaleTimeString()}] `) + message);
      this.rl.prompt(true);
    } else {
      console.log(message);
    }
  }

  /**
   * 获取状态图标
   */
  private getStatusIcon(status: string): string {
    switch (status) {
      case 'idle':
        return chalk.gray('○');
      case 'busy':
        return chalk.blue('●');
      case 'error':
        return chalk.red('●');
      case 'offline':
        return chalk.gray('◌');
      default:
        return chalk.gray('?');
    }
  }

  /**
   * 获取任务状态图标
   */
  private getTaskStatusIcon(status: string): string {
    switch (status) {
      case 'pending':
        return chalk.gray('○');
      case 'running':
        return chalk.blue('●');
      case 'completed':
        return chalk.green('✓');
      case 'failed':
        return chalk.red('✗');
      default:
        return chalk.gray('?');
    }
  }
}
