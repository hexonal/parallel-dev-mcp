/**
 * WorkerPool - Worker 池管理器
 *
 * Layer 2: 编排层组件
 * 负责 Worker 生命周期管理和状态追踪
 */

import { EventEmitter } from 'events';
import { Worker, WorkerStatus, ParallelDevConfig } from '../types';
import { WorktreeManager } from '../git/WorktreeManager';
import { TmuxController } from '../tmux/TmuxController';

/**
 * Worker 池统计信息
 */
export interface WorkerPoolStats {
  total: number;
  idle: number;
  busy: number;
  error: number;
}

/**
 * R7.1: Worker 恢复策略
 */
export interface RecoveryPolicy {
  maxRetries: number;
  retryDelayMs: number;
  autoRecover: boolean;
  heartbeatTimeoutMs: number;
}

/**
 * 默认恢复策略
 */
const DEFAULT_RECOVERY_POLICY: RecoveryPolicy = {
  maxRetries: 3,
  retryDelayMs: 5000,
  autoRecover: true,
  heartbeatTimeoutMs: 90000,
};

/**
 * WorkerPool 类
 *
 * 管理 Worker 池的创建、状态追踪和清理
 */
export class WorkerPool extends EventEmitter {
  private maxWorkers: number;
  private workers: Map<string, Worker> = new Map();
  private worktreeManager?: WorktreeManager;
  private tmuxController?: TmuxController;
  private recoveryPolicy: RecoveryPolicy = DEFAULT_RECOVERY_POLICY;
  private retryCounters: Map<string, number> = new Map();
  private projectRoot?: string;
  private config?: ParallelDevConfig;

  constructor(maxWorkers: number) {
    super();
    this.maxWorkers = maxWorkers;
  }

  /**
   * 初始化 Worker 池
   */
  async initialize(
    projectRoot: string,
    config: ParallelDevConfig
  ): Promise<void> {
    this.projectRoot = projectRoot;
    this.config = config;
    this.worktreeManager = new WorktreeManager(projectRoot, config.worktreeDir);

    // 不传参数，让 TmuxController 自动检测当前 tmux 会话名作为前缀
    this.tmuxController = new TmuxController();

    // 创建初始 Worker
    for (let i = 0; i < this.maxWorkers; i++) {
      const worker = this.createWorker(`worker-${i + 1}`);
      this.addWorker(worker);
    }

    this.emit('initialized', { workerCount: this.maxWorkers });
  }

  /**
   * 创建 Worker 对象
   */
  private createWorker(id: string): Worker {
    return {
      id,
      status: 'idle',
      worktreePath: '',
      tmuxSession: '',
      lastHeartbeat: new Date().toISOString(),
      completedTasks: 0,
      failedTasks: 0,
    };
  }

  /**
   * 添加 Worker
   */
  addWorker(worker: Worker): void {
    this.workers.set(worker.id, worker);
    this.emit('worker_added', { workerId: worker.id });
  }

  /**
   * 移除 Worker
   */
  removeWorker(workerId: string): void {
    if (this.workers.has(workerId)) {
      this.workers.delete(workerId);
      this.emit('worker_removed', { workerId });
    }
  }

  /**
   * 获取空闲 Worker
   */
  getIdleWorker(): Worker | undefined {
    for (const worker of this.workers.values()) {
      if (worker.status === 'idle') {
        return worker;
      }
    }
    return undefined;
  }

  /**
   * 设置 Worker 状态
   */
  setWorkerStatus(workerId: string, status: WorkerStatus): void {
    const worker = this.workers.get(workerId);
    if (worker) {
      const oldStatus = worker.status;
      worker.status = status;
      worker.lastHeartbeat = new Date().toISOString();

      this.emit('status_changed', { workerId, oldStatus, newStatus: status });
    }
  }

  /**
   * 获取 Worker 状态
   */
  getWorkerStatus(workerId: string): WorkerStatus | undefined {
    return this.workers.get(workerId)?.status;
  }

  /**
   * 获取指定 Worker
   */
  getWorker(workerId: string): Worker | undefined {
    return this.workers.get(workerId);
  }

  /**
   * 获取所有 Worker
   */
  getAllWorkers(): Worker[] {
    return Array.from(this.workers.values());
  }

  /**
   * 获取统计信息
   */
  getStats(): WorkerPoolStats {
    let idle = 0;
    let busy = 0;
    let error = 0;

    for (const worker of this.workers.values()) {
      switch (worker.status) {
        case 'idle':
          idle++;
          break;
        case 'busy':
          busy++;
          break;
        case 'error':
          error++;
          break;
      }
    }

    return {
      total: this.workers.size,
      idle,
      busy,
      error,
    };
  }

  /**
   * 更新 Worker 心跳
   */
  updateHeartbeat(workerId: string): void {
    const worker = this.workers.get(workerId);
    if (worker) {
      worker.lastHeartbeat = new Date().toISOString();
    }
  }

  /**
   * 增加 Worker 完成任务计数
   */
  incrementCompletedTasks(workerId: string): void {
    const worker = this.workers.get(workerId);
    if (worker) {
      worker.completedTasks++;
    }
  }

  /**
   * 增加 Worker 失败任务计数
   */
  incrementFailedTasks(workerId: string): void {
    const worker = this.workers.get(workerId);
    if (worker) {
      worker.failedTasks++;
    }
  }

  /**
   * 清理所有 Worker
   */
  async cleanup(): Promise<void> {
    // 清理 Tmux 会话
    if (this.tmuxController) {
      for (const worker of this.workers.values()) {
        if (worker.tmuxSession) {
          try {
            await this.tmuxController.killSession(worker.tmuxSession);
          } catch {
            // 忽略清理错误
          }
        }
      }
    }

    // 清理 Worktree
    if (this.worktreeManager) {
      for (const worker of this.workers.values()) {
        if (worker.worktreePath) {
          try {
            await this.worktreeManager.remove(worker.worktreePath);
          } catch {
            // 忽略清理错误
          }
        }
      }
    }

    // 清空 Worker 列表
    this.workers.clear();

    this.emit('cleanup_completed');
  }

  // ============================================================
  // R7.1: Worker 崩溃恢复
  // ============================================================

  /**
   * 设置恢复策略
   *
   * @param policy 恢复策略配置
   */
  setRecoveryPolicy(policy: Partial<RecoveryPolicy>): void {
    this.recoveryPolicy = { ...this.recoveryPolicy, ...policy };
    this.emit('recovery_policy_changed', { policy: this.recoveryPolicy });
  }

  /**
   * 获取恢复策略
   */
  getRecoveryPolicy(): RecoveryPolicy {
    return { ...this.recoveryPolicy };
  }

  /**
   * 检测崩溃的 Worker
   *
   * 崩溃条件：
   * - 心跳超时（超过 heartbeatTimeoutMs）
   * - 状态为 error
   */
  detectCrashedWorkers(): Worker[] {
    const now = Date.now();
    const crashedWorkers: Worker[] = [];

    for (const worker of this.workers.values()) {
      // 检查状态是否为 error
      if (worker.status === 'error') {
        crashedWorkers.push(worker);
        continue;
      }

      // 检查心跳超时
      const lastHeartbeat = new Date(worker.lastHeartbeat).getTime();
      const elapsed = now - lastHeartbeat;

      if (elapsed > this.recoveryPolicy.heartbeatTimeoutMs) {
        crashedWorkers.push(worker);
      }
    }

    if (crashedWorkers.length > 0) {
      this.emit('crashed_workers_detected', {
        count: crashedWorkers.length,
        workerIds: crashedWorkers.map((w) => w.id),
      });
    }

    return crashedWorkers;
  }

  /**
   * 恢复单个 Worker
   *
   * @param workerId Worker ID
   * @returns 是否恢复成功
   */
  async recoverWorker(workerId: string): Promise<boolean> {
    const worker = this.workers.get(workerId);
    if (!worker) {
      return false;
    }

    // 检查重试次数
    const retryCount = this.retryCounters.get(workerId) || 0;
    if (retryCount >= this.recoveryPolicy.maxRetries) {
      this.emit('recovery_exhausted', {
        workerId,
        retryCount,
        maxRetries: this.recoveryPolicy.maxRetries,
      });
      return false;
    }

    try {
      this.emit('recovery_started', { workerId, attempt: retryCount + 1 });

      // 1. 清理旧资源
      await this.cleanupWorkerResources(worker);

      // 2. 等待恢复延迟
      await this.delay(this.recoveryPolicy.retryDelayMs);

      // 3. 重建 Worker
      const newWorker = await this.restartWorker(workerId);

      // 4. 重置重试计数
      this.retryCounters.set(workerId, 0);

      this.emit('recovery_completed', { workerId, newWorker });
      return true;
    } catch (error) {
      // 增加重试计数
      this.retryCounters.set(workerId, retryCount + 1);

      const errorMessage = error instanceof Error ? error.message : String(error);
      this.emit('recovery_failed', {
        workerId,
        attempt: retryCount + 1,
        error: errorMessage,
      });

      return false;
    }
  }

  /**
   * 重启 Worker
   *
   * @param workerId Worker ID
   * @returns 重建后的 Worker
   */
  async restartWorker(workerId: string): Promise<Worker> {
    // 移除旧 Worker
    this.removeWorker(workerId);

    // 创建新 Worker
    const newWorker = this.createWorker(workerId);
    this.addWorker(newWorker);

    this.emit('worker_restarted', { workerId });

    return newWorker;
  }

  /**
   * 自动恢复所有崩溃的 Worker
   *
   * @returns 恢复结果
   */
  async autoRecoverAll(): Promise<{
    attempted: number;
    recovered: number;
    failed: number;
  }> {
    if (!this.recoveryPolicy.autoRecover) {
      return { attempted: 0, recovered: 0, failed: 0 };
    }

    const crashedWorkers = this.detectCrashedWorkers();
    let recovered = 0;
    let failed = 0;

    for (const worker of crashedWorkers) {
      const success = await this.recoverWorker(worker.id);
      if (success) {
        recovered++;
      } else {
        failed++;
      }
    }

    return {
      attempted: crashedWorkers.length,
      recovered,
      failed,
    };
  }

  /**
   * 清理 Worker 资源
   */
  private async cleanupWorkerResources(worker: Worker): Promise<void> {
    // 清理 Tmux 会话
    if (this.tmuxController && worker.tmuxSession) {
      try {
        await this.tmuxController.killSession(worker.tmuxSession);
      } catch {
        // 忽略清理错误
      }
    }

    // 清理 Worktree
    if (this.worktreeManager && worker.worktreePath) {
      try {
        await this.worktreeManager.remove(worker.worktreePath);
      } catch {
        // 忽略清理错误
      }
    }
  }

  /**
   * 延迟辅助函数
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
