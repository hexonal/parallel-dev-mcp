/**
 * SocketClient - 爆改自 Happy apiSocket.ts
 *
 * 新增功能：
 * - 双向 RPC 支持（Worker 可接收 Master 的 RPC 调用）
 * - 请求 ID 追踪（匹配请求和响应）
 * - 本地处理器注册
 * - TweetNaCl/Libsodium 加密（爆改自 Happy）
 *
 * 保留功能：
 * - Socket.IO 连接管理
 * - 自动重连
 * - 状态监听
 */

import { io, Socket } from 'socket.io-client';
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import {
  ConnectionStatus,
  SocketClientConfig,
  RpcRequest,
  RpcResponse,
  PendingRequest,
  RpcHandler,
} from './types';
import { SimpleEncryption } from '../encryption';

/**
 * 默认 RPC 超时时间（30秒）
 */
const DEFAULT_RPC_TIMEOUT_MS = 30000;

/**
 * 双向 RPC Socket 客户端
 *
 * 爆改自 Happy apiSocket.ts，新增：
 * - 本地处理器注册（让 Master 可以调用 Worker）
 * - 请求 ID 追踪
 * - RPC 响应匹配
 * - TweetNaCl/Libsodium 加密（爆改自 Happy）
 */
export class SocketClient extends EventEmitter {
  // 连接状态
  private socket: Socket | null = null;
  private config: SocketClientConfig;
  private currentStatus: ConnectionStatus = 'disconnected';

  // 双向 RPC 支持
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private handlers: Map<string, RpcHandler> = new Map();
  private rpcTimeoutMs: number;

  // 加密支持（爆改自 Happy）
  private encryption: SimpleEncryption | null = null;
  private encryptionEnabled: boolean = false;

  // 监听器
  private reconnectedListeners: Set<() => void> = new Set();
  private statusListeners: Set<(status: ConnectionStatus) => void> = new Set();

  constructor(config: SocketClientConfig) {
    super();
    this.config = config;
    this.rpcTimeoutMs = config.rpcTimeoutMs ?? DEFAULT_RPC_TIMEOUT_MS;

    // 初始化加密（如果提供了密钥）
    if (config.enableEncryption && config.encryptionKey) {
      this.encryption = new SimpleEncryption(config.encryptionKey);
      this.encryptionEnabled = true;
    }
  }

  // ============ 连接管理 ============

  /**
   * 连接到服务器
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.socket) {
        resolve();
        return;
      }

      this.updateStatus('connecting');

      this.socket = io(this.config.endpoint, {
        path: '/v1/parallel',
        auth: {
          token: this.config.token,
          workerId: this.config.workerId,
          clientType: 'worker',
        },
        transports: ['websocket'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: Infinity,
      });

      this.setupEventHandlers();

      // 等待连接成功或失败
      const onConnect = () => {
        cleanup();
        resolve();
      };

      const onError = (error: Error) => {
        cleanup();
        reject(error);
      };

      const cleanup = () => {
        this.socket?.off('connect', onConnect);
        this.socket?.off('connect_error', onError);
      };

      this.socket.once('connect', onConnect);
      this.socket.once('connect_error', onError);
    });
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.updateStatus('disconnected');
    this.clearPendingRequests('Socket disconnected');
  }

  /**
   * 检查是否已连接
   */
  isConnected(): boolean {
    return this.currentStatus === 'connected';
  }

  /**
   * 获取当前连接状态
   */
  getStatus(): ConnectionStatus {
    return this.currentStatus;
  }

  // ============ 双向 RPC：发起调用 ============

  /**
   * 发起 RPC 调用（子→父）
   *
   * Worker 调用 Master 或回复 Master
   * 如果启用加密，参数会被加密后传输
   */
  async rpc<TResult = unknown, TParams = unknown>(
    method: string,
    params: TParams
  ): Promise<TResult> {
    if (!this.socket || !this.isConnected()) {
      throw new Error('Socket not connected');
    }

    const requestId = this.generateRequestId();

    // 加密参数（如果启用）
    let encryptedParams: unknown = params;
    if (this.encryptionEnabled && this.encryption) {
      encryptedParams = await this.encryption.encryptRaw(params);
    }

    const request: RpcRequest = {
      id: requestId,
      method: `${this.config.workerId}:${method}`,
      params: encryptedParams,
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

      // 发送请求
      this.socket!.emit('rpc-request', request);
    });
  }

  // ============ 双向 RPC：注册处理器 ============

  /**
   * 注册本地 RPC 处理器
   *
   * 让 Master 可以调用 Worker 的方法
   */
  registerHandler<TRequest = unknown, TResponse = unknown>(
    method: string,
    handler: RpcHandler<TRequest, TResponse>
  ): void {
    const prefixedMethod = `${this.config.workerId}:${method}`;
    this.handlers.set(prefixedMethod, handler as RpcHandler);

    // 通知服务器注册了新处理器
    if (this.socket && this.isConnected()) {
      this.socket.emit('rpc-register', { method: prefixedMethod });
    }
  }

  /**
   * 注销本地 RPC 处理器
   */
  unregisterHandler(method: string): void {
    const prefixedMethod = `${this.config.workerId}:${method}`;
    this.handlers.delete(prefixedMethod);
  }

  /**
   * 检查是否注册了指定处理器
   */
  hasHandler(method: string): boolean {
    const prefixedMethod = `${this.config.workerId}:${method}`;
    return this.handlers.has(prefixedMethod);
  }

  // ============ 事件发送 ============

  /**
   * 发送事件到服务器
   */
  emit(event: string, data: unknown): boolean {
    if (!this.socket) {
      return false;
    }
    this.socket.emit(event, data);
    return true;
  }

  /**
   * 发送事件并等待确认
   */
  async emitWithAck<T = unknown>(event: string, data: unknown): Promise<T> {
    if (!this.socket) {
      throw new Error('Socket not connected');
    }
    return await this.socket.emitWithAck(event, data);
  }

  // ============ 监听器管理 ============

  /**
   * 监听重连事件
   */
  onReconnected(listener: () => void): () => void {
    this.reconnectedListeners.add(listener);
    return () => this.reconnectedListeners.delete(listener);
  }

  /**
   * 监听状态变化
   */
  onStatusChange(
    listener: (status: ConnectionStatus) => void
  ): () => void {
    this.statusListeners.add(listener);
    // 立即通知当前状态
    listener(this.currentStatus);
    return () => this.statusListeners.delete(listener);
  }

  // ============ 私有方法 ============

  /**
   * 更新连接状态
   */
  private updateStatus(status: ConnectionStatus): void {
    if (this.currentStatus !== status) {
      this.currentStatus = status;
      this.statusListeners.forEach((listener) => listener(status));
      this.emit('status', status);
    }
  }

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
   * 处理来自 Master 的 RPC 请求
   * 如果启用加密，会先解密参数，然后加密响应
   */
  private async handleRpcRequest(request: RpcRequest): Promise<void> {
    const handler = this.handlers.get(request.method);

    let response: RpcResponse;

    if (!handler) {
      response = {
        id: request.id,
        error: `Method not found: ${request.method}`,
        timestamp: Date.now(),
      };
    } else {
      try {
        // 解密参数（如果启用加密）
        let decryptedParams = request.params;
        if (this.encryptionEnabled && this.encryption && typeof request.params === 'string') {
          decryptedParams = await this.encryption.decryptRaw(request.params);
          if (decryptedParams === null) {
            throw new Error('Failed to decrypt request params');
          }
        }

        const result = await handler(decryptedParams);

        // 加密结果（如果启用加密）
        let encryptedResult: unknown = result;
        if (this.encryptionEnabled && this.encryption) {
          encryptedResult = await this.encryption.encryptRaw(result);
        }

        response = {
          id: request.id,
          result: encryptedResult,
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
    this.socket?.emit('rpc-response', response);
  }

  /**
   * 处理 RPC 响应
   * 如果启用加密，会先解密结果
   */
  private async handleRpcResponse(response: RpcResponse): Promise<void> {
    const pending = this.pendingRequests.get(response.id);

    if (!pending) {
      // 响应已超时或不存在
      return;
    }

    // 清理
    clearTimeout(pending.timeout);
    this.pendingRequests.delete(response.id);

    // 解析结果
    if (response.error) {
      pending.reject(new Error(response.error));
    } else {
      // 解密结果（如果启用加密）
      let decryptedResult = response.result;
      if (this.encryptionEnabled && this.encryption && typeof response.result === 'string') {
        decryptedResult = await this.encryption.decryptRaw(response.result);
        if (decryptedResult === null) {
          pending.reject(new Error('Failed to decrypt response result'));
          return;
        }
      }
      pending.resolve(decryptedResult);
    }
  }

  /**
   * 设置事件处理器
   */
  private setupEventHandlers(): void {
    if (!this.socket) return;

    // 连接成功
    this.socket.on('connect', () => {
      this.updateStatus('connected');

      // 重新注册所有处理器
      for (const [method] of this.handlers) {
        this.socket?.emit('rpc-register', { method });
      }

      // 通知重连
      if (!this.socket?.recovered) {
        this.reconnectedListeners.forEach((listener) => listener());
      }
    });

    // 断开连接
    this.socket.on('disconnect', () => {
      this.updateStatus('disconnected');
    });

    // 连接错误
    this.socket.on('connect_error', () => {
      this.updateStatus('error');
    });

    this.socket.on('error', () => {
      this.updateStatus('error');
    });

    // 处理来自 Master 的 RPC 请求
    this.socket.on('rpc-request', (request: RpcRequest) => {
      this.handleRpcRequest(request);
    });

    // 处理 RPC 响应
    this.socket.on('rpc-response', (response: RpcResponse) => {
      this.handleRpcResponse(response);
    });
  }
}
