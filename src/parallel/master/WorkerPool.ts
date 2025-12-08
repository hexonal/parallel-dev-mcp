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
 * WorkerPool 类
 *
 * 管理 Worker 池的创建、状态追踪和清理
 */
export class WorkerPool extends EventEmitter {
  private maxWorkers: number;
  private workers: Map<string, Worker> = new Map();
  private worktreeManager?: WorktreeManager;
  private tmuxController?: TmuxController;

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
    this.worktreeManager = new WorktreeManager(projectRoot, config.worktreeDir);

    this.tmuxController = new TmuxController('parallel-dev');

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
}
