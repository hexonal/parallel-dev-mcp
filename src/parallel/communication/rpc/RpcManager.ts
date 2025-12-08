/**
 * RpcManager - 爆改自 Happy RpcHandlerManager.ts
 *
 * 新增功能：
 * - 双向 RPC 调用（Master↔Worker）
 * - 请求 ID 追踪
 * - 超时处理
 * - 响应匹配
 *
 * 保留功能：
 * - 处理器注册
 * - 可选加密支持
 */

import { v4 as uuidv4 } from 'uuid';
import {
  RpcRequest,
  RpcResponse,
  PendingRequest,
  RpcHandler,
} from '../types';

/**
 * RPC 管理器配置
 */
export interface RpcManagerConfig {
  /** 作用域前缀（如 worker:xxx） */
  scopePrefix?: string;
  /** RPC 超时时间（毫秒） */
  timeoutMs?: number;
  /** 加密密钥（可选） */
  encryptionKey?: Uint8Array;
  /** 日志函数 */
  logger?: (message: string, data?: unknown) => void;
}

/**
 * 默认 RPC 超时时间（30秒）
 */
const DEFAULT_TIMEOUT_MS = 30000;

/**
 * RPC 发送函数类型
 */
export type RpcSendFunction = (
  event: string,
  data: unknown
) => void;

/**
 * 双向 RPC 管理器
 *
 * 爆改自 Happy RpcHandlerManager.ts，新增：
 * - 双向 RPC 调用支持
 * - 请求 ID 追踪和响应匹配
 * - 超时处理
 */
export class RpcManager {
  // 配置
  private scopePrefix: string;
  private timeoutMs: number;
  private logger: (message: string, data?: unknown) => void;

  // 处理器和待处理请求
  private handlers: Map<string, RpcHandler> = new Map();
  private pendingRequests: Map<string, PendingRequest> = new Map();

  // 发送函数（由外部注入）
  private sendFn: RpcSendFunction | null = null;

  constructor(config: RpcManagerConfig = {}) {
    this.scopePrefix = config.scopePrefix ?? '';
    this.timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.logger = config.logger ?? (() => {});
  }

  // ============ 初始化 ============

  /**
   * 设置发送函数
   *
   * 用于发送 RPC 请求和响应
   */
  setSendFunction(fn: RpcSendFunction): void {
    this.sendFn = fn;
  }

  // ============ 处理器注册 ============

  /**
   * 注册 RPC 处理器
   */
  registerHandler<TRequest = unknown, TResponse = unknown>(
    method: string,
    handler: RpcHandler<TRequest, TResponse>
  ): void {
    const prefixedMethod = this.getPrefixedMethod(method);
    this.handlers.set(prefixedMethod, handler as RpcHandler);
    this.logger('[RPC] Handler registered', { method: prefixedMethod });
  }

  /**
   * 注销 RPC 处理器
   */
  unregisterHandler(method: string): void {
    const prefixedMethod = this.getPrefixedMethod(method);
    this.handlers.delete(prefixedMethod);
    this.logger('[RPC] Handler unregistered', { method: prefixedMethod });
  }

  /**
   * 检查是否注册了指定处理器
   */
  hasHandler(method: string): boolean {
    const prefixedMethod = this.getPrefixedMethod(method);
    return this.handlers.has(prefixedMethod);
  }

  /**
   * 获取注册的处理器数量
   */
  getHandlerCount(): number {
    return this.handlers.size;
  }

  /**
   * 清除所有处理器
   */
  clearHandlers(): void {
    this.handlers.clear();
    this.logger('[RPC] All handlers cleared');
  }

  // ============ RPC 调用 ============

  /**
   * 发起 RPC 调用
   */
  async call<TResult = unknown, TParams = unknown>(
    method: string,
    params: TParams
  ): Promise<TResult> {
    if (!this.sendFn) {
      throw new Error('Send function not set');
    }

    const requestId = this.generateRequestId();
    const prefixedMethod = this.getPrefixedMethod(method);

    const request: RpcRequest = {
      id: requestId,
      method: prefixedMethod,
      params,
      timestamp: Date.now(),
    };

    return new Promise<TResult>((resolve, reject) => {
      // 设置超时
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        this.logger('[RPC] Request timeout', { method, requestId });
        reject(new Error(`RPC timeout: ${method}`));
      }, this.timeoutMs);

      // 记录待处理请求
      this.pendingRequests.set(requestId, {
        resolve: resolve as (value: unknown) => void,
        reject,
        timeout,
        method,
        createdAt: Date.now(),
      });

      // 发送请求
      this.sendFn!('rpc-request', request);
      this.logger('[RPC] Request sent', { method, requestId });
    });
  }

  /**
   * 调用 Worker 的方法（Master 端使用）
   */
  async callWorker<TResult = unknown, TParams = unknown>(
    workerId: string,
    method: string,
    params: TParams
  ): Promise<TResult> {
    return this.call<TResult, TParams>(`${workerId}:${method}`, params);
  }

  /**
   * 调用 Master 的方法（Worker 端使用）
   */
  async callMaster<TResult = unknown, TParams = unknown>(
    method: string,
    params: TParams
  ): Promise<TResult> {
    return this.call<TResult, TParams>(method, params);
  }

  // ============ 请求/响应处理 ============

  /**
   * 处理收到的 RPC 请求
   */
  async handleRequest(request: RpcRequest): Promise<void> {
    if (!this.sendFn) {
      return;
    }

    this.logger('[RPC] Request received', {
      method: request.method,
      id: request.id,
    });

    const handler = this.handlers.get(request.method);

    let response: RpcResponse;

    if (!handler) {
      this.logger('[RPC] Handler not found', { method: request.method });
      response = {
        id: request.id,
        error: `Method not found: ${request.method}`,
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
        this.logger('[RPC] Request handled successfully', {
          method: request.method,
          id: request.id,
        });
      } catch (error) {
        this.logger('[RPC] Handler error', {
          method: request.method,
          error,
        });
        response = {
          id: request.id,
          error: error instanceof Error ? error.message : 'Unknown error',
          timestamp: Date.now(),
        };
      }
    }

    // 发送响应
    this.sendFn('rpc-response', response);
  }

  /**
   * 处理收到的 RPC 响应
   */
  handleResponse(response: RpcResponse): void {
    const pending = this.pendingRequests.get(response.id);

    if (!pending) {
      this.logger('[RPC] Response for unknown request', { id: response.id });
      return;
    }

    // 清理
    clearTimeout(pending.timeout);
    this.pendingRequests.delete(response.id);

    // 解析结果
    if (response.error) {
      this.logger('[RPC] Response error', {
        id: response.id,
        error: response.error,
      });
      pending.reject(new Error(response.error));
    } else {
      this.logger('[RPC] Response success', { id: response.id });
      pending.resolve(response.result);
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
   * 获取带前缀的方法名
   */
  private getPrefixedMethod(method: string): string {
    return this.scopePrefix ? `${this.scopePrefix}:${method}` : method;
  }

  /**
   * 清理所有待处理请求
   */
  clearPendingRequests(reason: string): void {
    for (const [id, pending] of this.pendingRequests) {
      clearTimeout(pending.timeout);
      pending.reject(new Error(reason));
    }
    this.pendingRequests.clear();
    this.logger('[RPC] Pending requests cleared', { reason });
  }

  /**
   * 获取待处理请求数量
   */
  getPendingRequestCount(): number {
    return this.pendingRequests.size;
  }

  /**
   * 销毁管理器
   */
  destroy(): void {
    this.clearPendingRequests('RpcManager destroyed');
    this.clearHandlers();
    this.sendFn = null;
  }
}
