/**
 * StatusReporter - Worker 状态报告器
 *
 * 功能：
 * - 向 Master 报告任务状态（开始/完成/失败/进度）
 * - 心跳机制
 * - 日志发送
 */

import { SocketClient } from '../communication/SocketClient';
import { WorkerEventType } from '../communication/types';

/**
 * 任务结果
 */
export interface TaskResult {
  /** 任务 ID */
  taskId: string;
  /** 执行时长（毫秒） */
  durationMs: number;
  /** 产出物（如 commit hash） */
  output?: unknown;
  /** 额外信息 */
  metadata?: Record<string, unknown>;
}

/**
 * 状态报告器配置
 */
export interface StatusReporterConfig {
  /** 心跳间隔（毫秒，默认 30000） */
  heartbeatIntervalMs?: number;
  /** 是否自动启动心跳 */
  autoStartHeartbeat?: boolean;
}

/**
 * 默认心跳间隔（30秒）
 */
const DEFAULT_HEARTBEAT_INTERVAL_MS = 30000;

/**
 * Worker 状态报告器
 *
 * 负责向 Master 报告 Worker 的状态和任务进度
 */
export class StatusReporter {
  private socket: SocketClient;
  private workerId: string;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private heartbeatIntervalMs: number;

  constructor(
    socket: SocketClient,
    workerId: string,
    config: StatusReporterConfig = {}
  ) {
    this.socket = socket;
    this.workerId = workerId;
    this.heartbeatIntervalMs =
      config.heartbeatIntervalMs ?? DEFAULT_HEARTBEAT_INTERVAL_MS;

    if (config.autoStartHeartbeat) {
      this.startHeartbeat();
    }
  }

  // ============ 任务状态报告 ============

  /**
   * 报告任务开始
   */
  reportTaskStarted(taskId: string): void {
    this.sendEvent('task_started', {
      taskId,
      startedAt: new Date().toISOString(),
    });
  }

  /**
   * 报告任务完成
   */
  reportTaskCompleted(taskId: string, result: TaskResult): void {
    this.sendEvent('task_completed', {
      taskId,
      result,
      completedAt: new Date().toISOString(),
    });
  }

  /**
   * 报告任务失败
   */
  reportTaskFailed(taskId: string, error: string): void {
    this.sendEvent('task_failed', {
      taskId,
      error,
      failedAt: new Date().toISOString(),
    });
  }

  /**
   * 报告任务进度
   */
  reportProgress(
    taskId: string,
    progress: number,
    message?: string
  ): void {
    this.sendEvent('task_progress', {
      taskId,
      progress: Math.min(100, Math.max(0, progress)),
      message,
      timestamp: new Date().toISOString(),
    });
  }

  // ============ Worker 状态 ============

  /**
   * 报告 Worker 就绪
   */
  reportReady(): void {
    this.sendEvent('ready', {
      readyAt: new Date().toISOString(),
    });
  }

  /**
   * 报告状态更新
   */
  reportStatusUpdate(status: Record<string, unknown>): void {
    this.sendEvent('status_update', {
      ...status,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * 发送日志
   */
  reportLog(
    level: 'info' | 'warn' | 'error',
    message: string,
    data?: unknown
  ): void {
    this.sendEvent('log', {
      level,
      message,
      data,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * 报告错误
   */
  reportError(error: Error | string): void {
    this.sendEvent('error', {
      message: error instanceof Error ? error.message : error,
      stack: error instanceof Error ? error.stack : undefined,
      timestamp: new Date().toISOString(),
    });
  }

  // ============ 心跳管理 ============

  /**
   * 启动心跳
   */
  startHeartbeat(intervalMs?: number): void {
    if (this.heartbeatInterval) {
      return;
    }

    const interval = intervalMs ?? this.heartbeatIntervalMs;

    this.heartbeatInterval = setInterval(() => {
      this.sendHeartbeat();
    }, interval);

    // 立即发送一次心跳
    this.sendHeartbeat();
  }

  /**
   * 停止心跳
   */
  stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * 发送心跳
   */
  private sendHeartbeat(): void {
    this.socket.emit('heartbeat', {
      workerId: this.workerId,
      timestamp: new Date().toISOString(),
    });
  }

  // ============ 私有方法 ============

  /**
   * 发送事件
   */
  private sendEvent(type: WorkerEventType, payload: unknown): void {
    this.socket.emit(`worker:${type}`, {
      workerId: this.workerId,
      type,
      payload,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * 销毁报告器
   */
  destroy(): void {
    this.stopHeartbeat();
  }
}
