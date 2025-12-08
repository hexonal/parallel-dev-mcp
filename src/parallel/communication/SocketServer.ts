/**
 * SocketServer - Master 端 Socket 服务器
 *
 * 功能：
 * - 管理 Worker 连接
 * - 双向 RPC 支持（Master 可调用 Worker）
 * - 请求 ID 追踪（匹配请求和响应）
 * - 事件广播
 */

import { Server, Socket } from 'socket.io';
import { createServer, Server as HttpServer } from 'http';
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import {
  SocketServerConfig,
  RpcRequest,
  RpcResponse,
  PendingRequest,
  RpcHandler,
  ConnectionStatus,
} from './types';

/**
 * 默认 RPC 超时时间（30秒）
 */
const DEFAULT_RPC_TIMEOUT_MS = 30000;

/**
 * Worker 连接信息
 */
interface WorkerConnection {
  workerId: string;
  socket: Socket;
  connectedAt: number;
  lastHeartbeat: number;
  registeredMethods: Set<string>;
}

/**
 * Master Socket 服务器
 *
 * 管理 Worker 连接，支持双向 RPC 调用
 */
export class SocketServer extends EventEmitter {
  private io: Server | null = null;
  private httpServer: HttpServer | null = null;
  private config: SocketServerConfig;
  private rpcTimeoutMs: number;

  // Worker 管理
  private workers: Map<string, WorkerConnection> = new Map();

  // 双向 RPC 支持
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private handlers: Map<string, RpcHandler> = new Map();

  constructor(config: SocketServerConfig) {
    super();
    this.config = config;
    this.rpcTimeoutMs = config.rpcTimeoutMs ?? DEFAULT_RPC_TIMEOUT_MS;
  }

  // ============ 服务器管理 ============

  /**
   * 启动服务器
   */
  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.httpServer = createServer();

        this.io = new Server(this.httpServer, {
          path: '/v1/parallel',
          cors: {
            origin: '*',
            methods: ['GET', 'POST'],
          },
        });

        this.setupServerHandlers();

        this.httpServer.listen(this.config.port, () => {
          this.emit('started', { port: this.config.port });
          resolve();
        });

        this.httpServer.on('error', (error) => {
          reject(error);
        });
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * 停止服务器
   */
  async stop(): Promise<void> {
    // 清理所有待处理请求
    this.clearPendingRequests('Server stopping');

    // 断开所有 Worker
    for (const [workerId, worker] of this.workers) {
      worker.socket.disconnect(true);
    }
    this.workers.clear();

    // 关闭服务器
    return new Promise((resolve) => {
      if (this.io) {
        this.io.close(() => {
          this.io = null;
          this.httpServer = null;
          this.emit('stopped');
          resolve();
        });
      } else {
        resolve();
      }
    });
  }

  // ============ Worker 管理 ============

  /**
   * 获取已连接的 Worker ID 列表
   */
  getConnectedWorkers(): string[] {
    return Array.from(this.workers.keys());
  }

  /**
   * 获取 Worker 数量
   */
  getWorkerCount(): number {
    return this.workers.size;
  }

  /**
   * 检查 Worker 是否在线
   */
  isWorkerConnected(workerId: string): boolean {
    return this.workers.has(workerId);
  }

  /**
   * 获取 Worker 连接信息
   */
  getWorkerInfo(workerId: string): WorkerConnection | undefined {
    return this.workers.get(workerId);
  }

  // ============ 双向 RPC：发起调用 ============

  /**
   * 调用 Worker 的 RPC 方法（父→子）
   */
  async callWorker<TResult = unknown, TParams = unknown>(
    workerId: string,
    method: string,
    params: TParams
  ): Promise<TResult> {
    const worker = this.workers.get(workerId);

    if (!worker) {
      throw new Error(`Worker not connected: ${workerId}`);
    }

    const requestId = this.generateRequestId();
    const request: RpcRequest = {
      id: requestId,
      method: `${workerId}:${method}`,
      params,
      timestamp: Date.now(),
    };

    return new Promise<TResult>((resolve, reject) => {
      // 设置超时
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        reject(new Error(`RPC timeout: ${method}`));
      }, this.rpcTimeoutMs);

      // 记录待处理请求
      this.pendingRequests.set(requestId, {
        resolve: resolve as (value: unknown) => void,
        reject,
        timeout,
        method,
        createdAt: Date.now(),
      });

      // 发送请求到 Worker
      worker.socket.emit('rpc-request', request);
    });
  }

  // ============ 双向 RPC：注册处理器 ============

  /**
   * 注册 Master 端 RPC 处理器
   *
   * 让 Worker 可以调用 Master 的方法
   */
  registerHandler<TRequest = unknown, TResponse = unknown>(
    method: string,
    handler: RpcHandler<TRequest, TResponse>
  ): void {
    this.handlers.set(method, handler as RpcHandler);
  }

  /**
   * 注销 RPC 处理器
   */
  unregisterHandler(method: string): void {
    this.handlers.delete(method);
  }

  // ============ 事件发送 ============

  /**
   * 向指定 Worker 发送事件
   */
  sendToWorker(workerId: string, event: string, data: unknown): boolean {
    const worker = this.workers.get(workerId);

    if (!worker) {
      return false;
    }

    worker.socket.emit(event, data);
    return true;
  }

  /**
   * 向所有 Worker 广播事件
   */
  broadcast(event: string, data: unknown): void {
    if (this.io) {
      this.io.emit(event, data);
    }
  }

  // ============ 私有方法 ============

  /**
   * 生成请求 ID
   */
  private generateRequestId(): string {
    return uuidv4();
  }

  /**
   * 清理所有待处理的请求
   */
  private clearPendingRequests(reason: string): void {
    for (const [id, pending] of this.pendingRequests) {
      clearTimeout(pending.timeout);
      pending.reject(new Error(reason));
    }
    this.pendingRequests.clear();
  }

  /**
   * 处理来自 Worker 的 RPC 请求
   */
  private async handleRpcRequest(
    socket: Socket,
    request: RpcRequest
  ): Promise<void> {
    // 提取实际方法名（去掉 workerId 前缀）
    const parts = request.method.split(':');
    const method = parts.length > 1 ? parts.slice(1).join(':') : request.method;

    const handler = this.handlers.get(method);

    let response: RpcResponse;

    if (!handler) {
      response = {
        id: request.id,
        error: `Method not found: ${method}`,
        timestamp: Date.now(),
      };
    } else {
      try {
        const result = await handler(request.params);
        response = {
          id: request.id,
          result,
          timestamp: Date.now(),
        };
      } catch (error) {
        response = {
          id: request.id,
          error: error instanceof Error ? error.message : 'Unknown error',
          timestamp: Date.now(),
        };
      }
    }

    // 发送响应
    socket.emit('rpc-response', response);
  }

  /**
   * 处理 RPC 响应
   */
  private handleRpcResponse(response: RpcResponse): void {
    const pending = this.pendingRequests.get(response.id);

    if (!pending) {
      return;
    }

    // 清理
    clearTimeout(pending.timeout);
    this.pendingRequests.delete(response.id);

    // 解析结果
    if (response.error) {
      pending.reject(new Error(response.error));
    } else {
      pending.resolve(response.result);
    }
  }

  /**
   * 设置服务器事件处理器
   */
  private setupServerHandlers(): void {
    if (!this.io) return;

    this.io.on('connection', (socket: Socket) => {
      const workerId = socket.handshake.auth.workerId as string;

      if (!workerId) {
        socket.disconnect(true);
        return;
      }

      // 记录 Worker 连接
      const connection: WorkerConnection = {
        workerId,
        socket,
        connectedAt: Date.now(),
        lastHeartbeat: Date.now(),
        registeredMethods: new Set(),
      };

      this.workers.set(workerId, connection);
      this.emit('worker:connected', { workerId });

      // 处理断开连接
      socket.on('disconnect', () => {
        this.workers.delete(workerId);
        this.emit('worker:disconnected', { workerId });
      });

      // 处理心跳
      socket.on('heartbeat', () => {
        const worker = this.workers.get(workerId);
        if (worker) {
          worker.lastHeartbeat = Date.now();
        }
        this.emit('worker:heartbeat', { workerId });
      });

      // 处理 RPC 方法注册
      socket.on('rpc-register', (data: { method: string }) => {
        const worker = this.workers.get(workerId);
        if (worker) {
          worker.registeredMethods.add(data.method);
        }
      });

      // 处理来自 Worker 的 RPC 请求
      socket.on('rpc-request', (request: RpcRequest) => {
        this.handleRpcRequest(socket, request);
      });

      // 处理 RPC 响应
      socket.on('rpc-response', (response: RpcResponse) => {
        this.handleRpcResponse(response);
      });

      // 转发 Worker 事件
      socket.on('worker:task_started', (data) => {
        this.emit('worker:task_started', { workerId, ...data });
      });

      socket.on('worker:task_completed', (data) => {
        this.emit('worker:task_completed', { workerId, ...data });
      });

      socket.on('worker:task_failed', (data) => {
        this.emit('worker:task_failed', { workerId, ...data });
      });

      socket.on('worker:status_update', (data) => {
        this.emit('worker:status_update', { workerId, ...data });
      });
    });
  }
}
