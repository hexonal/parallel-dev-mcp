/**
 * MasterServer - REPL 专用的 Master Socket 服务
 *
 * 包装 SocketServer，提供 REPL 所需的高级功能：
 * - Worker 状态追踪
 * - 进度更新管理
 * - 日志收集
 * - 命令分发
 *
 * @module repl/MasterServer
 */

import { EventEmitter } from 'events';
import { SocketServer, SocketServerConfig } from '../parallel/communication';

/**
 * Worker 状态
 */
export interface WorkerState {
  id: string;
  status: 'idle' | 'running' | 'error' | 'disconnected';
  taskId?: string;
  taskTitle?: string;
  progress: number;
  message: string;
  connectedAt: number;
  lastUpdate: number;
  logs: LogEntry[];
}

/**
 * 日志条目
 */
export interface LogEntry {
  timestamp: number;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
}

/**
 * 进度更新事件
 */
export interface ProgressUpdate {
  workerId: string;
  taskId: string;
  percent: number;
  message: string;
}

/**
 * MasterServer 配置
 */
export interface MasterServerConfig {
  port: number;
  maxLogEntries?: number;
  enableEncryption?: boolean;
  encryptionKey?: Uint8Array;
}

/**
 * MasterServer - REPL 的通信核心
 */
export class MasterServer extends EventEmitter {
  private socketServer: SocketServer;
  private workers: Map<string, WorkerState> = new Map();
  private config: MasterServerConfig;
  private maxLogEntries: number;
  private running: boolean = false;

  constructor(config: MasterServerConfig) {
    super();
    this.config = config;
    this.maxLogEntries = config.maxLogEntries ?? 100;

    // 创建底层 Socket 服务器
    const socketConfig: SocketServerConfig = {
      port: config.port,
      enableEncryption: config.enableEncryption,
      encryptionKey: config.encryptionKey,
    };

    this.socketServer = new SocketServer(socketConfig);
    this.setupEventHandlers();
  }

  /**
   * 启动服务器
   */
  async start(): Promise<void> {
    if (this.running) {
      return;
    }

    await this.socketServer.start();
    this.running = true;
    this.emit('started', { port: this.config.port });
  }

  /**
   * 停止服务器
   */
  async stop(): Promise<void> {
    if (!this.running) {
      return;
    }

    await this.socketServer.stop();
    this.running = false;
    this.workers.clear();
    this.emit('stopped');
  }

  /**
   * 检查服务器是否运行中
   */
  isRunning(): boolean {
    return this.running;
  }

  /**
   * 获取服务器端口
   */
  getPort(): number {
    return this.config.port;
  }

  // ============ Worker 状态管理 ============

  /**
   * 获取所有 Worker 状态
   */
  getWorkers(): Map<string, WorkerState> {
    return new Map(this.workers);
  }

  /**
   * 获取指定 Worker 状态
   */
  getWorker(workerId: string): WorkerState | undefined {
    return this.workers.get(workerId);
  }

  /**
   * 获取 Worker 数量统计
   */
  getWorkerStats(): { total: number; idle: number; running: number; error: number } {
    let idle = 0;
    let running = 0;
    let error = 0;

    for (const worker of this.workers.values()) {
      switch (worker.status) {
        case 'idle':
          idle++;
          break;
        case 'running':
          running++;
          break;
        case 'error':
          error++;
          break;
      }
    }

    return {
      total: this.workers.size,
      idle,
      running,
      error,
    };
  }

  /**
   * 获取 Worker 日志
   */
  getWorkerLogs(workerId: string, limit?: number): LogEntry[] {
    const worker = this.workers.get(workerId);
    if (!worker) {
      return [];
    }

    const logs = worker.logs;
    if (limit && limit < logs.length) {
      return logs.slice(-limit);
    }
    return [...logs];
  }

  // ============ 命令发送 ============

  /**
   * 向 Worker 分配任务
   */
  async assignTask(
    workerId: string,
    taskId: string,
    task: unknown
  ): Promise<boolean> {
    if (!this.socketServer.isWorkerConnected(workerId)) {
      return false;
    }

    this.socketServer.sendToWorker(workerId, 'task:assign', { taskId, task });

    // 更新本地状态
    const worker = this.workers.get(workerId);
    if (worker) {
      worker.status = 'running';
      worker.taskId = taskId;
      worker.progress = 0;
      worker.message = 'Task assigned';
      worker.lastUpdate = Date.now();
    }

    return true;
  }

  /**
   * 取消 Worker 的任务
   */
  async cancelTask(workerId: string): Promise<boolean> {
    if (!this.socketServer.isWorkerConnected(workerId)) {
      return false;
    }

    const worker = this.workers.get(workerId);
    if (!worker || !worker.taskId) {
      return false;
    }

    this.socketServer.sendToWorker(workerId, 'task:cancel', {
      taskId: worker.taskId,
    });

    return true;
  }

  /**
   * 广播命令到所有 Worker
   */
  broadcast(event: string, data: unknown): void {
    this.socketServer.broadcast(event, data);
  }

  /**
   * 调用 Worker 的 RPC 方法
   */
  async callWorker<T = unknown>(
    workerId: string,
    method: string,
    params: unknown
  ): Promise<T> {
    return this.socketServer.callWorker<T>(workerId, method, params);
  }

  // ============ 私有方法 ============

  /**
   * 设置事件处理器
   */
  private setupEventHandlers(): void {
    // Worker 连接
    this.socketServer.on('worker:connected', ({ workerId }) => {
      const state: WorkerState = {
        id: workerId,
        status: 'idle',
        progress: 0,
        message: 'Connected',
        connectedAt: Date.now(),
        lastUpdate: Date.now(),
        logs: [],
      };

      this.workers.set(workerId, state);
      this.emit('worker:connected', { workerId, state });
    });

    // Worker 断开
    this.socketServer.on('worker:disconnected', ({ workerId }) => {
      const worker = this.workers.get(workerId);
      if (worker) {
        worker.status = 'disconnected';
        worker.lastUpdate = Date.now();
      }
      this.emit('worker:disconnected', { workerId });
    });

    // Worker 心跳
    this.socketServer.on('worker:heartbeat', ({ workerId }) => {
      const worker = this.workers.get(workerId);
      if (worker) {
        worker.lastUpdate = Date.now();
      }
      this.emit('worker:heartbeat', { workerId });
    });

    // 任务开始
    // StatusReporter 发送格式: { workerId, type, payload: { taskId, startedAt }, timestamp }
    this.socketServer.on(
      'worker:task_started',
      (data: { workerId: string; taskId?: string; taskTitle?: string; payload?: { taskId: string } }) => {
        const workerId = data.workerId;
        // 支持两种格式：直接格式和嵌套 payload 格式
        const taskId = data.taskId || data.payload?.taskId;
        const taskTitle = data.taskTitle;

        const worker = this.workers.get(workerId);
        if (worker) {
          worker.status = 'running';
          worker.taskId = taskId;
          worker.taskTitle = taskTitle;
          worker.progress = 0;
          worker.message = 'Task started';
          worker.lastUpdate = Date.now();
          this.addLog(workerId, 'info', `Started task: ${taskTitle || taskId}`);
        }
        this.emit('worker:task_started', { workerId, taskId, taskTitle });
      }
    );

    // 任务完成
    // StatusReporter 发送格式: { workerId, type, payload: { taskId, result, completedAt }, timestamp }
    this.socketServer.on(
      'worker:task_completed',
      (data: { workerId: string; taskId?: string; result?: unknown; payload?: { taskId: string; result: unknown } }) => {
        const workerId = data.workerId;
        // 支持两种格式：直接格式和嵌套 payload 格式
        const taskId = data.taskId || data.payload?.taskId;
        const result = data.result || data.payload?.result;

        const worker = this.workers.get(workerId);
        if (worker) {
          worker.status = 'idle';
          worker.progress = 100;
          worker.message = 'Task completed';
          worker.lastUpdate = Date.now();
          this.addLog(workerId, 'info', `Completed task: ${worker.taskTitle || taskId}`);
          worker.taskId = undefined;
          worker.taskTitle = undefined;
        }
        this.emit('worker:task_completed', { workerId, taskId, result });
      }
    );

    // 任务失败
    // StatusReporter 发送格式: { workerId, type, payload: { taskId, error, failedAt }, timestamp }
    this.socketServer.on(
      'worker:task_failed',
      (data: { workerId: string; taskId?: string; error?: string; payload?: { taskId: string; error: string } }) => {
        const workerId = data.workerId;
        // 支持两种格式：直接格式和嵌套 payload 格式
        const taskId = data.taskId || data.payload?.taskId;
        const error = data.error || data.payload?.error;

        const worker = this.workers.get(workerId);
        if (worker) {
          worker.status = 'error';
          worker.message = `Failed: ${error}`;
          worker.lastUpdate = Date.now();
          this.addLog(workerId, 'error', `Task failed: ${error}`);
        }
        this.emit('worker:task_failed', { workerId, taskId, error });
      }
    );

    // 状态更新（包含进度）
    this.socketServer.on(
      'worker:status_update',
      ({ workerId, status, progress, message, taskId }) => {
        const worker = this.workers.get(workerId);
        if (worker) {
          if (status) worker.status = status;
          if (typeof progress === 'number') worker.progress = progress;
          if (message) worker.message = message;
          worker.lastUpdate = Date.now();

          // 进度更新日志（只记录关键点）
          if (progress && (progress === 25 || progress === 50 || progress === 75)) {
            this.addLog(workerId, 'info', `Progress: ${progress}% - ${message || ''}`);
          }
        }

        const update: ProgressUpdate = {
          workerId,
          taskId: taskId || worker?.taskId || '',
          percent: progress || 0,
          message: message || '',
        };

        this.emit('worker:progress', update);
        this.emit('worker:status_update', { workerId, status, progress, message });
      }
    );

    // 合并请求
    this.socketServer.on(
      'worker:merge_request',
      ({ workerId, taskId, branchName }) => {
        this.addLog(workerId, 'info', `Merge request received for branch: ${branchName}`);
        this.emit('worker:merge_request', { workerId, taskId, branchName });
      }
    );
  }

  /**
   * 添加日志条目
   */
  private addLog(workerId: string, level: LogEntry['level'], message: string): void {
    const worker = this.workers.get(workerId);
    if (!worker) {
      return;
    }

    const entry: LogEntry = {
      timestamp: Date.now(),
      level,
      message,
    };

    worker.logs.push(entry);

    // 限制日志数量
    if (worker.logs.length > this.maxLogEntries) {
      worker.logs = worker.logs.slice(-this.maxLogEntries);
    }

    this.emit('worker:log', { workerId, entry });
  }
}
